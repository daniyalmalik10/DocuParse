from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from bson import ObjectId
from docuparse_contracts import JobStatus, ResumeExtraction

from app.tasks import _run_extraction

DOCUMENT_ID = str(ObjectId())

FAKE_DOC = {
    "_id": ObjectId(DOCUMENT_ID),
    "filename": "resume.pdf",
    "file_path": "/data/uploads/resume.pdf",
    "user_id": "user1",
}

FAKE_EXTRACTION = ResumeExtraction(
    full_name="Jane Doe",
    email="jane@example.com",
    skills=["Python"],
    experience=[],
    education=[],
)


def _make_task_mock(retries: int = 0, max_retries: int = 3) -> MagicMock:
    task = MagicMock()
    task.request.retries = retries
    task.max_retries = max_retries
    task.retry = MagicMock(side_effect=Exception("retry-called"))
    return task


def _make_db_mock(doc=FAKE_DOC) -> MagicMock:
    db = MagicMock()
    db.extraction_jobs.update_one = AsyncMock()
    db.documents.find_one = AsyncMock(return_value=doc)
    return db


@pytest.mark.asyncio
async def test_happy_path_marks_completed() -> None:
    task = _make_task_mock()
    db = _make_db_mock()

    with (
        patch("app.tasks.AsyncIOMotorClient") as mock_client_cls,
        patch("app.tasks.get_settings") as mock_settings,
        patch("app.tasks.extract_text", return_value="resume text"),
        patch("app.tasks.GroqProvider") as mock_provider_cls,
    ):
        mock_client_cls.return_value.__getitem__ = MagicMock(return_value=db)
        mock_client_cls.return_value.close = MagicMock()
        mock_settings.return_value = MagicMock(
            mongo_uri="mongodb://localhost",
            mongo_db="test",
            groq_api_key="key",
            groq_model="model",
        )
        mock_provider_cls.return_value.extract_resume.return_value = FAKE_EXTRACTION

        await _run_extraction(task, DOCUMENT_ID)

    calls = db.extraction_jobs.update_one.call_args_list
    final_call = calls[-1]
    assert final_call[0][1]["$set"]["status"] == JobStatus.completed.value
    assert final_call[0][1]["$set"]["extraction"]["full_name"] == "Jane Doe"


@pytest.mark.asyncio
async def test_document_not_found_marks_failed() -> None:
    task = _make_task_mock()
    db = _make_db_mock(doc=None)

    with (
        patch("app.tasks.AsyncIOMotorClient") as mock_client_cls,
        patch("app.tasks.get_settings") as mock_settings,
    ):
        mock_client_cls.return_value.__getitem__ = MagicMock(return_value=db)
        mock_client_cls.return_value.close = MagicMock()
        mock_settings.return_value = MagicMock(
            mongo_uri="mongodb://localhost",
            mongo_db="test",
            groq_api_key="key",
            groq_model="model",
        )

        with pytest.raises(ValueError):
            await _run_extraction(task, DOCUMENT_ID)

    calls = db.extraction_jobs.update_one.call_args_list
    final_call = calls[-1]
    assert final_call[0][1]["$set"]["status"] == JobStatus.failed.value


@pytest.mark.asyncio
async def test_llm_http_error_triggers_retry_when_retries_remain() -> None:
    task = _make_task_mock(retries=0, max_retries=3)
    db = _make_db_mock()

    http_err = httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())

    with (
        patch("app.tasks.AsyncIOMotorClient") as mock_client_cls,
        patch("app.tasks.get_settings") as mock_settings,
        patch("app.tasks.extract_text", return_value="text"),
        patch("app.tasks.GroqProvider") as mock_provider_cls,
    ):
        mock_client_cls.return_value.__getitem__ = MagicMock(return_value=db)
        mock_client_cls.return_value.close = MagicMock()
        mock_settings.return_value = MagicMock(
            mongo_uri="mongodb://localhost",
            mongo_db="test",
            groq_api_key="key",
            groq_model="model",
        )
        mock_provider_cls.return_value.extract_resume.side_effect = http_err

        with pytest.raises(Exception, match="retry-called"):
            await _run_extraction(task, DOCUMENT_ID)

    task.retry.assert_called_once()


@pytest.mark.asyncio
async def test_llm_http_error_marks_failed_when_retries_exhausted() -> None:
    task = _make_task_mock(retries=3, max_retries=3)
    db = _make_db_mock()

    http_err = httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())

    with (
        patch("app.tasks.AsyncIOMotorClient") as mock_client_cls,
        patch("app.tasks.get_settings") as mock_settings,
        patch("app.tasks.extract_text", return_value="text"),
        patch("app.tasks.GroqProvider") as mock_provider_cls,
    ):
        mock_client_cls.return_value.__getitem__ = MagicMock(return_value=db)
        mock_client_cls.return_value.close = MagicMock()
        mock_settings.return_value = MagicMock(
            mongo_uri="mongodb://localhost",
            mongo_db="test",
            groq_api_key="key",
            groq_model="model",
        )
        mock_provider_cls.return_value.extract_resume.side_effect = http_err

        await _run_extraction(task, DOCUMENT_ID)

    task.retry.assert_not_called()
    calls = db.extraction_jobs.update_one.call_args_list
    final_call = calls[-1]
    assert final_call[0][1]["$set"]["status"] == JobStatus.failed.value


@pytest.mark.asyncio
async def test_text_extraction_error_marks_failed() -> None:
    task = _make_task_mock()
    db = _make_db_mock()

    with (
        patch("app.tasks.AsyncIOMotorClient") as mock_client_cls,
        patch("app.tasks.get_settings") as mock_settings,
        patch("app.tasks.extract_text", side_effect=ValueError("bad file")),
    ):
        mock_client_cls.return_value.__getitem__ = MagicMock(return_value=db)
        mock_client_cls.return_value.close = MagicMock()
        mock_settings.return_value = MagicMock(
            mongo_uri="mongodb://localhost",
            mongo_db="test",
            groq_api_key="key",
            groq_model="model",
        )

        with pytest.raises(ValueError):
            await _run_extraction(task, DOCUMENT_ID)

    calls = db.extraction_jobs.update_one.call_args_list
    final_call = calls[-1]
    assert final_call[0][1]["$set"]["status"] == JobStatus.failed.value
    assert "bad file" in final_call[0][1]["$set"]["error_message"]
