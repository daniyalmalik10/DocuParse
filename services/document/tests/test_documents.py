from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from tests.helpers import AsyncCursorMock

USER_HEADERS = {"x-user-id": "user-abc"}
OTHER_USER_HEADERS = {"x-user-id": "user-xyz"}

NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _doc(doc_id: ObjectId, user_id: str = "user-abc", file_path: str = "/data/uploads/file.pdf"):
    return {
        "_id": doc_id,
        "filename": "resume.pdf",
        "content_type": "application/pdf",
        "size": 1024,
        "user_id": user_id,
        "uploaded_at": NOW,
        "file_path": file_path,
    }


def _job(doc_id: ObjectId, status: str = "pending", extraction=None, error_message=None):
    return {
        "_id": ObjectId(),
        "document_id": str(doc_id),
        "status": status,
        "created_at": NOW,
        "error_message": error_message,
        "extraction": extraction,
    }


# ── List ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_returns_user_documents(client, mock_db):
    doc_id = ObjectId()
    mock_db.documents.find = MagicMock(return_value=AsyncCursorMock([_doc(doc_id)]))
    mock_db.extraction_jobs.find_one.return_value = _job(doc_id)

    response = await client.get("/documents/", headers=USER_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["document_id"] == str(doc_id)


@pytest.mark.asyncio
async def test_list_find_called_with_user_id_filter(client, mock_db):
    mock_db.documents.find = MagicMock(return_value=AsyncCursorMock([]))

    await client.get("/documents/", headers=USER_HEADERS)
    mock_db.documents.find.assert_called_once_with({"user_id": "user-abc"})


@pytest.mark.asyncio
async def test_list_empty_returns_empty_list(client, mock_db):
    mock_db.documents.find = MagicMock(return_value=AsyncCursorMock([]))

    response = await client.get("/documents/", headers=USER_HEADERS)
    assert response.status_code == 200
    assert response.json()["items"] == []


# ── Get ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_returns_document_detail(client, mock_db):
    doc_id = ObjectId()
    mock_db.documents.find_one.return_value = _doc(doc_id)
    mock_db.extraction_jobs.find_one.return_value = _job(doc_id, status="pending")

    response = await client.get(f"/documents/{doc_id}", headers=USER_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == str(doc_id)
    assert body["filename"] == "resume.pdf"
    assert body["status"] == "pending"
    assert body["extraction"] is None


@pytest.mark.asyncio
async def test_get_completed_document_includes_extraction(client, mock_db):
    doc_id = ObjectId()
    extraction_data = {
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "phone": None,
        "location": None,
        "summary": None,
        "skills": ["Python", "FastAPI"],
        "experience": [],
        "education": [],
    }
    mock_db.documents.find_one.return_value = _doc(doc_id)
    mock_db.extraction_jobs.find_one.return_value = _job(
        doc_id, status="completed", extraction=extraction_data
    )

    response = await client.get(f"/documents/{doc_id}", headers=USER_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["extraction"]["full_name"] == "Jane Doe"
    assert body["extraction"]["skills"] == ["Python", "FastAPI"]


@pytest.mark.asyncio
async def test_get_returns_404_for_other_users_document(client, mock_db):
    doc_id = ObjectId()
    mock_db.documents.find_one.return_value = None  # ownership filter miss

    response = await client.get(f"/documents/{doc_id}", headers=OTHER_USER_HEADERS)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_invalid_object_id_returns_400(client):
    response = await client.get("/documents/not-an-objectid", headers=USER_HEADERS)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_nonexistent_returns_404(client, mock_db):
    mock_db.documents.find_one.return_value = None
    response = await client.get(f"/documents/{ObjectId()}", headers=USER_HEADERS)
    assert response.status_code == 404


# ── Delete ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_returns_204(client, mock_db, tmp_path):
    doc_id = ObjectId()
    fake_file = tmp_path / "file.pdf"
    fake_file.write_bytes(b"content")
    mock_db.documents.find_one.return_value = _doc(doc_id, file_path=str(fake_file))

    response = await client.delete(f"/documents/{doc_id}", headers=USER_HEADERS)
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_removes_file_and_db_records(client, mock_db, tmp_path):
    doc_id = ObjectId()
    fake_file = tmp_path / "file.pdf"
    fake_file.write_bytes(b"content")
    mock_db.documents.find_one.return_value = _doc(doc_id, file_path=str(fake_file))

    await client.delete(f"/documents/{doc_id}", headers=USER_HEADERS)

    assert not fake_file.exists()
    mock_db.documents.delete_one.assert_called_once()
    mock_db.extraction_jobs.delete_many.assert_called_once_with({"document_id": str(doc_id)})


@pytest.mark.asyncio
async def test_delete_missing_file_does_not_raise(client, mock_db, tmp_path):
    doc_id = ObjectId()
    nonexistent = str(tmp_path / "ghost.pdf")
    mock_db.documents.find_one.return_value = _doc(doc_id, file_path=nonexistent)

    response = await client.delete(f"/documents/{doc_id}", headers=USER_HEADERS)
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_other_users_document_returns_404(client, mock_db):
    doc_id = ObjectId()
    mock_db.documents.find_one.return_value = None

    response = await client.delete(f"/documents/{doc_id}", headers=OTHER_USER_HEADERS)
    assert response.status_code == 404
