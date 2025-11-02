from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "docuparse"
    upload_dir: str = "/data/uploads"
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
