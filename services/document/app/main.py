from fastapi import FastAPI

app = FastAPI(title="DocuParse Document Service", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "document"}
