import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import settings
from app.models.asset import AccessibilityAsset
from app.schemas.asset import AssetUploadResponse
from app.services import storage_service

router = APIRouter()

ALLOWED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ("PPTX", "pptx"),
    "application/pdf": ("PDF", "pdf"),
    "video/mp4": ("MP4", "mp4"),
}

# Some clients send incorrect MIME for pptx; also accept by extension
EXTENSION_FALLBACK = {
    "pptx": ("PPTX", "pptx"),
    "pdf": ("PDF", "pdf"),
    "mp4": ("MP4", "mp4"),
}


def _resolve_source_type(file: UploadFile) -> tuple[str, str]:
    """Return (SOURCE_TYPE, extension) or raise HTTPException."""
    if file.content_type and file.content_type in ALLOWED_MIME_TYPES:
        return ALLOWED_MIME_TYPES[file.content_type]

    # Fall back to extension
    if file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower()
        if ext in EXTENSION_FALLBACK:
            return EXTENSION_FALLBACK[ext]

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail=f"Unsupported file type. Upload PPTX, PDF, or MP4. Got: {file.content_type}",
    )


@router.post("/assets/upload", response_model=AssetUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_asset(
    file: Annotated[UploadFile, File(description="PPTX, PDF, or MP4 file")],
    course_id: Annotated[str | None, Form()] = None,
    db: Session = Depends(get_db),
) -> AssetUploadResponse:
    source_type, extension = _resolve_source_type(file)

    # Read and check file size
    data = await file.read()
    if len(data) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.max_upload_size_bytes // (1024 * 1024)} MB",
        )

    asset_id = uuid.uuid4()

    # Persist to local storage
    source_location = await storage_service.save_upload(asset_id, extension, data)

    # Create DB record
    asset = AccessibilityAsset(
        asset_id=asset_id,
        course_id=course_id,
        original_filename=file.filename or f"upload.{extension}",
        source_type=source_type,
        source_location=source_location,
        processing_status="PENDING",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    # Dispatch Celery pipeline
    from app.tasks.pipeline import process_asset_pipeline

    task = process_asset_pipeline.delay(str(asset_id))

    return AssetUploadResponse(
        asset_id=asset_id,
        original_filename=asset.original_filename,
        source_type=source_type,
        processing_status="PENDING",
        task_id=task.id,
    )
