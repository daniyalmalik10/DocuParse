from datetime import datetime, timedelta
from unittest.mock import MagicMock

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.jwt_utils import sign_access_token, sign_refresh_token


class TestRegister:
    async def test_returns_token_pair(self, client, mock_db, test_settings):
        inserted_id = ObjectId()
        mock_db.users.insert_one.return_value = MagicMock(inserted_id=inserted_id)

        resp = await client.post(
            "/auth/register", json={"email": "user@example.com", "password": "password123"}
        )

        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_duplicate_email_returns_409(self, client, mock_db):
        mock_db.users.insert_one.side_effect = DuplicateKeyError("duplicate")

        resp = await client.post(
            "/auth/register", json={"email": "dup@example.com", "password": "password123"}
        )

        assert resp.status_code == 409
        assert resp.json()["detail"] == "Email already registered"

    async def test_weak_password_returns_422(self, client):
        resp = await client.post(
            "/auth/register", json={"email": "user@example.com", "password": "short"}
        )
        assert resp.status_code == 422

    async def test_invalid_email_returns_422(self, client):
        resp = await client.post(
            "/auth/register", json={"email": "not-an-email", "password": "password123"}
        )
        assert resp.status_code == 422


class TestLogin:
    async def test_returns_token_pair(self, client, mock_db, test_settings):
        from passlib.context import CryptContext

        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto").hash("correctpassword")
        user_id = ObjectId()
        mock_db.users.find_one.return_value = {
            "_id": user_id,
            "email": "user@example.com",
            "hashed_password": pwd,
        }

        resp = await client.post(
            "/auth/login", json={"email": "user@example.com", "password": "correctpassword"}
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_wrong_password_returns_401(self, client, mock_db, test_settings):
        from passlib.context import CryptContext

        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto").hash("correctpassword")
        mock_db.users.find_one.return_value = {
            "_id": ObjectId(),
            "email": "user@example.com",
            "hashed_password": pwd,
        }

        resp = await client.post(
            "/auth/login", json={"email": "user@example.com", "password": "wrongpassword"}
        )

        assert resp.status_code == 401

    async def test_unknown_email_returns_401(self, client, mock_db):
        mock_db.users.find_one.return_value = None

        resp = await client.post(
            "/auth/login", json={"email": "nobody@example.com", "password": "password123"}
        )

        assert resp.status_code == 401

    async def test_generic_error_message(self, client, mock_db):
        mock_db.users.find_one.return_value = None

        resp = await client.post(
            "/auth/login", json={"email": "nobody@example.com", "password": "password123"}
        )

        assert resp.json()["detail"] == "Invalid credentials"


class TestRefresh:
    async def test_valid_refresh_token_returns_new_access_token(self, client, test_settings):
        user_id = str(ObjectId())
        refresh_token = sign_refresh_token(user_id, test_settings)

        resp = await client.post(
            "/auth/refresh", headers={"Authorization": f"Bearer {refresh_token}"}
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" not in data

    async def test_access_token_to_refresh_returns_401(self, client, test_settings):
        user_id = str(ObjectId())
        access_token = sign_access_token(user_id, test_settings)

        resp = await client.post(
            "/auth/refresh", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert resp.status_code == 401

    async def test_expired_token_returns_401(self, client, test_settings):
        from datetime import UTC

        from jose import jwt

        now = datetime.now(UTC).replace(tzinfo=None)
        claims = {
            "sub": str(ObjectId()),
            "type": "refresh",
            "iat": now - timedelta(days=8),
            "exp": now - timedelta(days=1),
        }
        expired_token = jwt.encode(claims, test_settings.private_key_pem, algorithm="RS256")

        resp = await client.post(
            "/auth/refresh", headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert resp.status_code == 401

    async def test_missing_header_returns_401(self, client):
        resp = await client.post("/auth/refresh")
        assert resp.status_code == 401


class TestMe:
    async def test_returns_user_info(self, client, mock_db, test_settings):
        user_id = str(ObjectId())
        access_token = sign_access_token(user_id, test_settings)
        mock_db.users.find_one.return_value = {"_id": ObjectId(user_id), "email": "me@example.com"}

        resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == user_id
        assert data["email"] == "me@example.com"

    async def test_no_header_returns_401(self, client):
        resp = await client.get("/auth/me")
        assert resp.status_code == 401

    async def test_refresh_token_returns_401(self, client, test_settings):
        user_id = str(ObjectId())
        refresh_token = sign_refresh_token(user_id, test_settings)

        resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {refresh_token}"})

        assert resp.status_code == 401
