from datetime import datetime, timezone

import pytest

from docuparse_contracts import (
    Education,
    ErrorResponse,
    ExtractionJob,
    JobStatus,
    ResumeExtraction,
    UploadMetadata,
    WorkExperience,
)

NOW = datetime(2026, 4, 18, 12, 0, 0, tzinfo=timezone.utc)


def test_job_status_values():
    assert JobStatus.pending == "pending"
    assert JobStatus.processing == "processing"
    assert JobStatus.completed == "completed"
    assert JobStatus.failed == "failed"


def test_work_experience_minimal():
    exp = WorkExperience(company="Acme", title="Engineer", start="2022-01")
    assert exp.end is None
    assert exp.bullets == []


def test_work_experience_full():
    exp = WorkExperience(
        company="Acme",
        title="Senior Engineer",
        start="2020-01",
        end="2023-06",
        bullets=["Led team of 5", "Reduced latency by 40%"],
    )
    assert len(exp.bullets) == 2


def test_education_minimal():
    edu = Education(institution="MIT", degree="B.Sc. Computer Science")
    assert edu.year is None


def test_education_full():
    edu = Education(institution="MIT", degree="B.Sc. Computer Science", year="2018")
    assert edu.year == "2018"


def test_resume_extraction_minimal():
    r = ResumeExtraction(full_name="Jane Doe")
    assert r.email is None
    assert r.skills == []
    assert r.experience == []
    assert r.education == []


def test_resume_extraction_nested():
    r = ResumeExtraction(
        full_name="Jane Doe",
        email="jane@example.com",
        phone="+1-555-0100",
        location="New York, NY",
        summary="Experienced engineer.",
        skills=["Python", "FastAPI", "MongoDB"],
        experience=[
            WorkExperience(company="Acme", title="Engineer", start="2020-01", end="2023-06")
        ],
        education=[Education(institution="MIT", degree="B.Sc. CS", year="2019")],
    )
    assert r.skills == ["Python", "FastAPI", "MongoDB"]
    assert r.experience[0].company == "Acme"
    assert r.education[0].institution == "MIT"


def test_upload_metadata():
    m = UploadMetadata(
        filename="resume.pdf",
        content_type="application/pdf",
        size=102400,
        user_id="user-abc",
        uploaded_at=NOW,
    )
    assert m.size == 102400
    assert m.uploaded_at == NOW


def test_extraction_job():
    job = ExtractionJob(
        job_id="job-1",
        document_id="doc-1",
        status=JobStatus.pending,
        created_at=NOW,
    )
    assert job.status == JobStatus.pending
    assert job.status == "pending"


def test_error_response_with_code():
    e = ErrorResponse(detail="File too large", code="FILE_TOO_LARGE")
    assert e.code == "FILE_TOO_LARGE"


def test_error_response_without_code():
    e = ErrorResponse(detail="Something went wrong")
    assert e.code is None
