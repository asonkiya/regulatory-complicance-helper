import uuid
from datetime import datetime

from pydantic import BaseModel


class AssetUploadResponse(BaseModel):
    asset_id: uuid.UUID
    original_filename: str
    source_type: str
    processing_status: str
    task_id: str


class AssetResponse(BaseModel):
    asset_id: uuid.UUID
    course_id: str | None
    original_filename: str
    source_type: str
    processing_status: str
    file_version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssetListResponse(BaseModel):
    assets: list[AssetResponse]
    total: int
    page: int
    page_size: int
