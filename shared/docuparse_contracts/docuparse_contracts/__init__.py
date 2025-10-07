from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class WorkExperience(BaseModel):
    company: str
    title: str
    start: str
    end: Optional[str] = None
    bullets: List[str] = []


class Education(BaseModel):
    institution: str
    degree: str
    year: Optional[str] = None


class ResumeExtraction(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str] = []
    experience: List[WorkExperience] = []
    education: List[Education] = []


class UploadMetadata(BaseModel):
    filename: str
    content_type: str
    size: int
    user_id: str
    uploaded_at: datetime


class ExtractionJob(BaseModel):
    job_id: str
    document_id: str
    status: JobStatus
    created_at: datetime


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
