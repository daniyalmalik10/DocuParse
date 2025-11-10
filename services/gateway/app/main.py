from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import get_motor_client
from app.routers.auth import router as auth_router
from app.routers.proxy import get_http_client
from app.routers.proxy import router as proxy_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    client = get_motor_client()
    db = client[settings.mongo_db]
    await db.users.create_index("email", unique=True)
    yield
    await get_http_client().aclose()
    get_motor_client().close()


app = FastAPI(title="DocuParse Gateway", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(proxy_router, tags=["proxy"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "gateway"}
