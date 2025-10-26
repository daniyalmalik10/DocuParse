import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId
from bson.errors import InvalidId
from celery import Celery
from docuparse_contracts import JobStatus, ResumeExtraction
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.celery_client import get_celery_app
from app.config import Settings, get_settings
from app.database import get_db
from app.dependencies import get_current_user_id
from app.models import DocumentDetail, DocumentListResponse, DocumentSummary, UploadResponse

EXTRACT_TASK_NAME = "worker.app.tasks.extract_resume"
EXTRACT_QUEUE = "extraction"

ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}

router = APIRouter()


@router.post("/upload", status_code=201, response_model=UploadResponse)
async def upload_document(
    file: UploadFile,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
    celery_app: Celery = Depends(get_celery_app),
) -> UploadResponse:
    content_type = file.content_type or ""
    ext = ALLOWED_CONTENT_TYPES.get(content_type)
    if ext is None:
        raise HTTPException(
            status_code=422, detail="Unsupported file type. Upload PDF or DOCX only."
        )

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File exceeds the 5 MB limit.")

    file_name = f"{uuid.uuid4()}.{ext}"
    file_path = str(Path(settings.upload_dir) / file_name)
    await asyncio.to_thread(Path(file_path).write_bytes, content)

    now = datetime.now(timezone.utc)
    doc_result = await db.documents.insert_one(
        {
            "filename": file.filename or file_name,
            "content_type": content_type,
            "size": len(content),
            "user_id": user_id,
            "uploaded_at": now,
            "file_path": file_path,
        }
    )
    document_id = str(doc_result.inserted_id)

    job_result = await db.extraction_jobs.insert_one(
        {
            "document_id": document_id,
            "status": JobStatus.pending.value,
            "created_at": now,
            "error_message": None,
            "extraction": None,
        }
    )
    job_id = str(job_result.inserted_id)

    celery_app.send_task(EXTRACT_TASK_NAME, args=[document_id], queue=EXTRACT_QUEUE)

    return UploadResponse(document_id=document_id, job_id=job_id, status=JobStatus.pending)


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> DocumentListResponse:
    items: list[DocumentSummary] = []
    async for doc in db.documents.find({"user_id": user_id}).sort("uploaded_at", -1):
        job = await db.extraction_jobs.find_one({"document_id": str(doc["_id"])})
        status = JobStatus(job["status"]) if job else JobStatus.pending
        items.append(
            DocumentSummary(
                document_id=str(doc["_id"]),
                filename=doc["filename"],
                content_type=doc["content_type"],
                size=doc["size"],
                uploaded_at=doc["uploaded_at"],
                status=status,
            )
        )
    return DocumentListResponse(items=items)


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> DocumentDetail:
    try:
        oid = ObjectId(document_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid document ID.")

    doc = await db.documents.find_one({"_id": oid, "user_id": user_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    job = await db.extraction_jobs.find_one({"document_id": document_id})
    status = JobStatus(job["status"]) if job else JobStatus.pending
    error_message = job.get("error_message") if job else None
    extraction: ResumeExtraction | None = None
    if job and job.get("extraction"):
        extraction = ResumeExtraction(**job["extraction"])

    return DocumentDetail(
        document_id=str(doc["_id"]),
        filename=doc["filename"],
        content_type=doc["content_type"],
        size=doc["size"],
        uploaded_at=doc["uploaded_at"],
        status=status,
        error_message=error_message,
        extraction=extraction,
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    try:
        oid = ObjectId(document_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid document ID.")

    doc = await db.documents.find_one({"_id": oid, "user_id": user_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    await asyncio.to_thread(Path(doc["file_path"]).unlink, missing_ok=True)
    await db.extraction_jobs.delete_many({"document_id": document_id})
    await db.documents.delete_one({"_id": oid})
