from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient

from app.config import Settings, get_settings
from app.database import get_db
from app.routers.proxy import get_http_client


@pytest.fixture(scope="session")
def test_rsa_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


@pytest.fixture(scope="session")
def test_settings(test_rsa_keys):
    private_pem, public_pem = test_rsa_keys
    return Settings(
        jwt_private_key=private_pem.replace("\n", "\\n"),
        jwt_public_key=public_pem.replace("\n", "\\n"),
        mongo_uri="mongodb://localhost:27017",
        mongo_db="test_db",
        document_service_url="http://document-test:8001",
    )


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.users = MagicMock()
    db.users.find_one = AsyncMock()
    db.users.insert_one = AsyncMock()
    db.users.create_index = AsyncMock()
    return db


@pytest.fixture
def mock_http_client():
    return AsyncMock(spec_set=["request", "aclose"])


@pytest.fixture
async def client(mock_db, mock_http_client, test_settings):
    motor_mock = MagicMock()
    motor_mock.__getitem__ = MagicMock(return_value=mock_db)

    async def override_get_db():
        yield mock_db

    from app.main import app

    # Use FastAPI's dependency_overrides so Depends() picks up test versions
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_http_client] = lambda: mock_http_client
    app.dependency_overrides[get_settings] = lambda: test_settings

    with patch("app.database.get_motor_client", return_value=motor_mock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()
