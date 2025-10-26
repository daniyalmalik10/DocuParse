from datetime import datetime
from typing import Optional

from docuparse_contracts import JobStatus, ResumeExtraction
from pydantic import BaseModel


class UploadResponse(BaseModel):
    document_id: str
    job_id: str
    status: JobStatus


class DocumentSummary(BaseModel):
    document_id: str
    filename: str
    content_type: str
    size: int
    uploaded_at: datetime
    status: JobStatus


class DocumentDetail(BaseModel):
    document_id: str
    filename: str
    content_type: str
    size: int
    uploaded_at: datetime
    status: JobStatus
    error_message: Optional[str] = None
    extraction: Optional[ResumeExtraction] = None


class DocumentListResponse(BaseModel):
    items: list[DocumentSummary]
