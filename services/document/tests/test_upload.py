from pathlib import Path
from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from app.api.documents import EXTRACT_QUEUE, EXTRACT_TASK_NAME

UPLOAD_URL = "/documents/upload"
USER_HEADERS = {"x-user-id": "user-abc"}

PDF_CONTENT_TYPE = "application/pdf"
DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _make_insert_result(oid: ObjectId | None = None) -> MagicMock:
    result = MagicMock()
    result.inserted_id = oid or ObjectId()
    return result


@pytest.fixture
def mock_inserts(mock_db):
    doc_id = ObjectId()
    job_id = ObjectId()
    mock_db.documents.insert_one.return_value = _make_insert_result(doc_id)
    mock_db.extraction_jobs.insert_one.return_value = _make_insert_result(job_id)
    return doc_id, job_id


@pytest.mark.asyncio
async def test_upload_pdf_returns_201(client, mock_inserts):
    doc_id, job_id = mock_inserts
    response = await client.post(
        UPLOAD_URL,
        headers=USER_HEADERS,
        files={"file": ("resume.pdf", b"%PDF-1.4 fake content", PDF_CONTENT_TYPE)},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["document_id"] == str(doc_id)
    assert body["job_id"] == str(job_id)
    assert body["status"] == "pending"


@pytest.mark.asyncio
async def test_upload_docx_returns_201(client, mock_inserts):
    doc_id, job_id = mock_inserts
    response = await client.post(
        UPLOAD_URL,
        headers=USER_HEADERS,
        files={"file": ("resume.docx", b"PK\x03\x04 fake docx", DOCX_CONTENT_TYPE)},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_upload_invalid_type_returns_422(client):
    response = await client.post(
        UPLOAD_URL,
        headers=USER_HEADERS,
        files={"file": ("resume.txt", b"plain text", "text/plain")},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_oversized_returns_413(client, test_settings, mock_db):
    # Lower the limit via a fresh settings override
    from app.config import get_settings

    small_settings = test_settings.model_copy(update={"max_upload_bytes": 10})
    from app.main import app

    app.dependency_overrides[get_settings] = lambda: small_settings
    response = await client.post(
        UPLOAD_URL,
        headers=USER_HEADERS,
        files={"file": ("resume.pdf", b"A" * 11, PDF_CONTENT_TYPE)},
    )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_upload_missing_user_id_returns_401(client):
    response = await client.post(
        UPLOAD_URL,
        files={"file": ("resume.pdf", b"%PDF-1.4", PDF_CONTENT_TYPE)},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_file_written_to_disk(client, mock_inserts, test_settings):
    await client.post(
        UPLOAD_URL,
        headers=USER_HEADERS,
        files={"file": ("resume.pdf", b"%PDF-1.4 content", PDF_CONTENT_TYPE)},
    )
    upload_dir = Path(test_settings.upload_dir)
    pdf_files = list(upload_dir.glob("*.pdf"))
    assert len(pdf_files) == 1


@pytest.mark.asyncio
async def test_celery_task_enqueued(client, mock_inserts, mock_celery):
    doc_id, _ = mock_inserts
    await client.post(
        UPLOAD_URL,
        headers=USER_HEADERS,
        files={"file": ("resume.pdf", b"%PDF-1.4 content", PDF_CONTENT_TYPE)},
    )
    mock_celery.send_task.assert_called_once_with(
        EXTRACT_TASK_NAME,
        args=[str(doc_id)],
        queue=EXTRACT_QUEUE,
    )
