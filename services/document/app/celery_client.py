from functools import lru_cache

from celery import Celery

from app.config import get_settings


@lru_cache(maxsize=1)
def get_celery_app() -> Celery:
    settings = get_settings()
    return Celery(broker=settings.redis_url, backend=settings.redis_url)
