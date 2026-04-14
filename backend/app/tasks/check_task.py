"""
Check task: runs all rule-based accessibility checkers against
the normalized document and bulk-inserts AccessibilityIssue rows.
"""
import json
import logging

from app.tasks.celery_app import celery_app
from app.tasks.utils import get_db_session, set_asset_status, set_stage_in_redis

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.check_task.check_asset", queue="default")
def check_asset(self, asset_id: str) -> str:
    """Run all accessibility checkers. Returns asset_id."""
    set_stage_in_redis(asset_id, "CHECKING")
    self.update_state(state="STARTED", meta={"stage": "CHECKING", "asset_id": asset_id})

    with get_db_session() as db:
        from app.models.asset import AccessibilityAsset
        from app.processing.normalizers import NormalizedDocument

        asset = db.get(AccessibilityAsset, asset_id)
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")

        set_asset_status(db, asset, "CHECKING")

        try:
            # Load normalized document
            with open(asset.normalized_content_ref) as f:
                raw = json.load(f)
            doc = NormalizedDocument.from_dict(raw)

            # Run all checkers
            from app.processing.checkers.alt_text_checker import check_alt_text
            from app.processing.checkers.caption_checker import check_captions
            from app.processing.checkers.contrast_checker import check_contrast
            from app.processing.checkers.pdf_content_checker import check_pdf_content
            from app.processing.checkers.pdf_tag_checker import check_pdf_tags
            from app.processing.checkers.structure_checker import check_structure

            all_issues = []
            for checker in [
                check_alt_text,
                check_structure,
                check_contrast,
                check_pdf_tags,
                check_pdf_content,
                check_captions,
            ]:
                issues = checker(doc)
                all_issues.extend(issues)

            # Bulk insert
            if all_issues:
                db.bulk_insert_mappings(
                    __import__("app.models.issue", fromlist=["AccessibilityIssue"]).AccessibilityIssue,
                    [
                        {
                            "asset_id": asset_id,
                            "issue_type": i.issue_type,
                            "severity": i.severity,
                            "location_in_asset": i.location_in_asset,
                            "fix_recommendation": i.fix_recommendation,
                            "auto_fixable": i.auto_fixable,
                            "confidence_score": i.confidence_score,
                            "review_status": "PENDING",
                        }
                        for i in all_issues
                    ],
                )

            db.commit()
            logger.info(
                "Checked asset %s: found %d issues", asset_id, len(all_issues)
            )

        except Exception as exc:
            set_asset_status(db, asset, "FAILED")
            logger.exception("Checking failed for asset %s", asset_id)
            raise self.retry(exc=exc, countdown=30, max_retries=2) from exc

    return asset_id
