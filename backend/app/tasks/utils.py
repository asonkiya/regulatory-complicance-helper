"""Shared utilities for Celery tasks."""
from contextlib import contextmanager
from collections.abc import Generator

import redis

from app.config import settings
from app.database import SessionLocal

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def set_stage_in_redis(asset_id: str, stage: str) -> None:
    """Write the current pipeline stage so the jobs endpoint can read it."""
    get_redis().setex(f"asset:{asset_id}:stage", 3600, stage)


@contextmanager
def get_db_session() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def set_asset_status(db, asset, status: str) -> None:
    asset.processing_status = status
    db.commit()
