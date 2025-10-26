from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongo_uri: str = "mongodb://mongo:27017"
    mongo_db: str = "docuparse"
    redis_url: str = "redis://redis:6379/0"
    upload_dir: str = "/data/uploads"
    max_upload_bytes: int = 5_242_880

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
