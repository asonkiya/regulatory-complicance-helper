import os
import uuid
from pathlib import Path

import aiofiles

from app.config import settings


def get_asset_dir(asset_id: str | uuid.UUID) -> Path:
    path = Path(settings.storage_base_path) / str(asset_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_asset_original_path(asset_id: str | uuid.UUID, extension: str) -> Path:
    return get_asset_dir(asset_id) / f"original.{extension}"


async def save_upload(asset_id: str | uuid.UUID, extension: str, data: bytes) -> str:
    dest = get_asset_original_path(asset_id, extension)
    async with aiofiles.open(dest, "wb") as f:
        await f.write(data)
    return str(dest)


def get_asset_file_path(asset_id: str | uuid.UUID, filename: str) -> Path:
    return get_asset_dir(asset_id) / filename


def asset_file_exists(asset_id: str | uuid.UUID, filename: str) -> bool:
    return get_asset_file_path(asset_id, filename).exists()
