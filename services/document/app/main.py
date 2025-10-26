from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.documents import router as documents_router
from app.config import get_settings
from app.database import get_motor_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    client = get_motor_client()
    db = client[settings.mongo_db]
    await db.documents.create_index(
        [("user_id", 1), ("uploaded_at", -1)],
        name="user_id_uploaded_at_desc",
    )
    yield
    get_motor_client().close()


app = FastAPI(title="DocuParse Document Service", version="0.1.0", lifespan=lifespan)
app.include_router(documents_router, prefix="/documents", tags=["documents"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "document"}
