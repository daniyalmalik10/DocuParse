from datetime import UTC, datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, Header, HTTPException
from jose import JWTError
from motor.motor_asyncio import AsyncIOMotorDatabase
from passlib.context import CryptContext
from pymongo.errors import DuplicateKeyError

from app.config import Settings, get_settings
from app.database import get_db
from app.dependencies import get_current_user_id
from app.jwt_utils import decode_token, sign_access_token, sign_refresh_token
from app.models import AccessTokenResponse, LoginRequest, MeResponse, RegisterRequest, TokenPair

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/register", status_code=201, response_model=TokenPair)
async def register(
    body: RegisterRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenPair:
    hashed = pwd_context.hash(body.password)
    doc = {"email": body.email, "hashed_password": hashed, "created_at": datetime.now(UTC)}
    try:
        result = await db.users.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Email already registered")
    user_id = str(result.inserted_id)
    return TokenPair(
        access_token=sign_access_token(user_id, settings),
        refresh_token=sign_refresh_token(user_id, settings),
    )


@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenPair:
    doc = await db.users.find_one({"email": body.email})
    if not doc or not pwd_context.verify(body.password, doc["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user_id = str(doc["_id"])
    return TokenPair(
        access_token=sign_access_token(user_id, settings),
        refresh_token=sign_refresh_token(user_id, settings),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> AccessTokenResponse:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = authorization.removeprefix("Bearer ")
    try:
        claims = decode_token(token, settings)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if claims.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token is not a refresh token")
    return AccessTokenResponse(access_token=sign_access_token(claims["sub"], settings))


@router.get("/me", response_model=MeResponse)
async def me(
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> MeResponse:
    doc = await db.users.find_one({"_id": ObjectId(user_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    return MeResponse(id=user_id, email=doc["email"])
