from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.celery_client import get_celery_app
from app.config import Settings, get_settings
from app.database import get_db
from app.main import app
from tests.helpers import AsyncCursorMock


@pytest.fixture
def test_settings(tmp_path):
    return Settings(
        mongo_uri="mongodb://localhost:27017",
        mongo_db="test_db",
        redis_url="redis://localhost:6379/0",
        upload_dir=str(tmp_path),
        max_upload_bytes=5_242_880,
    )


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.documents = MagicMock()
    db.documents.insert_one = AsyncMock()
    db.documents.find_one = AsyncMock()
    db.documents.find = MagicMock(return_value=AsyncCursorMock([]))
    db.documents.delete_one = AsyncMock()
    db.documents.create_index = AsyncMock()
    db.extraction_jobs = MagicMock()
    db.extraction_jobs.insert_one = AsyncMock()
    db.extraction_jobs.find_one = AsyncMock()
    db.extraction_jobs.delete_many = AsyncMock()
    return db


@pytest.fixture
def mock_celery():
    celery = MagicMock()
    celery.send_task = MagicMock()
    return celery


@pytest.fixture
async def client(test_settings, mock_db, mock_celery):
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_celery_app] = lambda: mock_celery

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
