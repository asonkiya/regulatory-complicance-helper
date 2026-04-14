import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.asset import AccessibilityAsset
from app.schemas.asset import AssetListResponse, AssetResponse

router = APIRouter()


@router.get("/assets", response_model=AssetListResponse)
def list_assets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_type: str | None = Query(None),
    processing_status: str | None = Query(None),
    db: Session = Depends(get_db),
) -> AssetListResponse:
    query = select(AccessibilityAsset)

    if source_type:
        query = query.where(AccessibilityAsset.source_type == source_type.upper())
    if processing_status:
        query = query.where(AccessibilityAsset.processing_status == processing_status.upper())

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    assets = db.scalars(
        query.order_by(AccessibilityAsset.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return AssetListResponse(
        assets=[AssetResponse.model_validate(a) for a in assets],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/assets/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: uuid.UUID, db: Session = Depends(get_db)) -> AssetResponse:
    asset = db.get(AccessibilityAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return AssetResponse.model_validate(asset)
