import asyncio

import httpx
from bson import ObjectId
from docuparse_contracts import JobStatus
from motor.motor_asyncio import AsyncIOMotorClient

from app.celery_app import celery_app
from app.config import get_settings
from app.llm_provider import GroqProvider
from app.text_extraction import extract_text


@celery_app.task(
    name="worker.app.tasks.extract_resume",
    bind=True,
    max_retries=3,
)
def extract_resume(self, document_id: str) -> None:
    asyncio.run(_run_extraction(self, document_id))


async def _run_extraction(task, document_id: str) -> None:
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client[settings.mongo_db]
    try:
        await db.extraction_jobs.update_one(
            {"document_id": document_id},
            {"$set": {"status": JobStatus.processing.value}},
        )

        doc = await db.documents.find_one({"_id": ObjectId(document_id)})
        if doc is None:
            raise ValueError(f"Document {document_id} not found in database")

        raw_text = extract_text(doc["file_path"])

        provider = GroqProvider(settings.groq_api_key, settings.groq_model)
        extraction = provider.extract_resume(raw_text)

        await db.extraction_jobs.update_one(
            {"document_id": document_id},
            {
                "$set": {
                    "status": JobStatus.completed.value,
                    "extraction": extraction.model_dump(),
                    "error_message": None,
                }
            },
        )
    except httpx.HTTPStatusError as exc:
        if task.request.retries < task.max_retries:
            raise task.retry(exc=exc, countdown=5 * (2**task.request.retries))
        await db.extraction_jobs.update_one(
            {"document_id": document_id},
            {"$set": {"status": JobStatus.failed.value, "error_message": str(exc)}},
        )
    except Exception as exc:
        await db.extraction_jobs.update_one(
            {"document_id": document_id},
            {"$set": {"status": JobStatus.failed.value, "error_message": str(exc)}},
        )
        raise
    finally:
        client.close()
