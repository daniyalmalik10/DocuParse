from fastapi import Depends, Header, HTTPException
from jose import JWTError

from app.config import Settings, get_settings
from app.jwt_utils import decode_token


async def get_current_user_id(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = authorization.removeprefix("Bearer ")
    try:
        claims = decode_token(token, settings)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if claims.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token is not an access token")
    return claims["sub"]
