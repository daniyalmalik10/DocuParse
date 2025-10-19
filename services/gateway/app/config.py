from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    jwt_private_key: str
    jwt_public_key: str
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    mongo_uri: str = "mongodb://mongo:27017"
    mongo_db: str = "docuparse"
    document_service_url: str = "http://document:8001"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def private_key_pem(self) -> str:
        return self.jwt_private_key.replace("\\n", "\n")

    @property
    def public_key_pem(self) -> str:
        return self.jwt_public_key.replace("\\n", "\n")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
