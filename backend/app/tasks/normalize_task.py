"""
Normalization task: parses the uploaded file into a NormalizedDocument
and saves it to {asset_id}/normalized.json.
"""
import json
import logging

from app.tasks.celery_app import celery_app
from app.tasks.utils import get_db_session, set_asset_status, set_stage_in_redis

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.normalize_task.normalize_asset", queue="default")
def normalize_asset(self, asset_id: str) -> str:
    """Normalize the asset. Returns asset_id for the next task in the chain."""
    set_stage_in_redis(asset_id, "NORMALIZING")
    self.update_state(state="STARTED", meta={"stage": "NORMALIZING", "asset_id": asset_id})

    with get_db_session() as db:
        from app.models.asset import AccessibilityAsset

        asset = db.get(AccessibilityAsset, asset_id)
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")

        set_asset_status(db, asset, "NORMALIZING")

        try:
            source_type = asset.source_type
            source_location = asset.source_location

            if source_type == "PPTX":
                from app.processing.normalizers.pptx_normalizer import normalize_pptx

                doc = normalize_pptx(asset_id, source_location)
            elif source_type == "PDF":
                from app.processing.normalizers.pdf_normalizer import normalize_pdf

                doc = normalize_pdf(asset_id, source_location)
            elif source_type == "MP4":
                from app.processing.normalizers.video_normalizer import normalize_video

                doc = normalize_video(asset_id, source_location)
            else:
                raise ValueError(f"Unsupported source_type: {source_type}")

            # Save normalized JSON
            from app.services.storage_service import get_asset_dir

            normalized_path = get_asset_dir(asset_id) / "normalized.json"
            with open(normalized_path, "w") as f:
                json.dump(doc.to_dict(), f, default=str)

            asset.normalized_content_ref = str(normalized_path)
            db.commit()

            logger.info("Normalized asset %s (%s)", asset_id, source_type)

        except Exception as exc:
            set_asset_status(db, asset, "FAILED")
            logger.exception("Normalization failed for asset %s", asset_id)
            raise self.retry(exc=exc, countdown=30, max_retries=2) from exc

    return asset_id
