from datetime import UTC, datetime, timedelta

from jose import jwt

from app.config import Settings


def sign_access_token(user_id: str, settings: Settings) -> str:
    now = datetime.now(UTC).replace(tzinfo=None)
    claims = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
    }
    return jwt.encode(claims, settings.private_key_pem, algorithm="RS256")


def sign_refresh_token(user_id: str, settings: Settings) -> str:
    now = datetime.now(UTC).replace(tzinfo=None)
    claims = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_refresh_token_expire_days),
    }
    return jwt.encode(claims, settings.private_key_pem, algorithm="RS256")


def decode_token(token: str, settings: Settings) -> dict:
    return jwt.decode(token, settings.public_key_pem, algorithms=["RS256"])
