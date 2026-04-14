"""
Remediation task: uses Claude to generate fixes for auto-fixable issues.
Runs on the ai_remediation queue.
"""
import logging

from app.tasks.celery_app import celery_app
from app.tasks.utils import get_db_session, set_asset_status, set_stage_in_redis

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.remediate_task.remediate_asset",
    queue="ai_remediation",
    soft_time_limit=600,
)
def remediate_asset(self, asset_id: str) -> str:
    """Generate AI fixes for all auto-fixable issues. Returns asset_id."""
    set_stage_in_redis(asset_id, "REMEDIATING")
    self.update_state(state="STARTED", meta={"stage": "REMEDIATING", "asset_id": asset_id})

    with get_db_session() as db:
        from sqlalchemy import select

        from app.models.asset import AccessibilityAsset
        from app.models.issue import AccessibilityIssue

        asset = db.get(AccessibilityAsset, asset_id)
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")

        set_asset_status(db, asset, "REMEDIATING")

        try:
            issues = db.scalars(
                select(AccessibilityIssue).where(
                    AccessibilityIssue.asset_id == asset_id,
                    AccessibilityIssue.auto_fixable.is_(True),
                    AccessibilityIssue.review_status == "PENDING",
                )
            ).all()

            for issue in issues:
                _remediate_issue(db, asset, issue)

            db.commit()
            logger.info("Remediated asset %s: processed %d issues", asset_id, len(issues))

        except Exception as exc:
            set_asset_status(db, asset, "FAILED")
            logger.exception("Remediation failed for asset %s", asset_id)
            raise self.retry(exc=exc, countdown=60, max_retries=3) from exc

    return asset_id


def _remediate_issue(db, asset, issue) -> None:
    """Dispatch to the appropriate remediator for a given issue type."""
    from app.models.artifact import GeneratedArtifact

    if issue.issue_type in ("MISSING_ALT_TEXT", "INADEQUATE_ALT_TEXT"):
        from app.processing.remediators.alt_text_generator import generate_alt_text_for_issue

        result = generate_alt_text_for_issue(asset, issue)
        artifact = GeneratedArtifact(
            asset_id=asset.asset_id,
            issue_id=issue.issue_id,
            artifact_type="ALT_TEXT",
            generation_status="COMPLETE",
            content_snapshot=result.alt_text,
        )
        db.add(artifact)
        issue.fix_recommendation = result.alt_text
        issue.confidence_score = result.confidence

    elif issue.issue_type == "MISSING_DOCUMENT_TITLE":
        from app.processing.remediators.document_title_generator import generate_title_for_issue

        result = generate_title_for_issue(asset, issue)
        artifact = GeneratedArtifact(
            asset_id=asset.asset_id,
            issue_id=issue.issue_id,
            artifact_type="DOCUMENT_TITLE",
            generation_status="COMPLETE",
            content_snapshot=result.title,
        )
        db.add(artifact)
        issue.fix_recommendation = result.title
        issue.confidence_score = result.confidence

    elif issue.issue_type == "MISSING_CAPTIONS":
        from app.processing.remediators.caption_generator import generate_captions_for_asset

        result = generate_captions_for_asset(asset)
        if result:
            for artifact_type, path in result.items():
                artifact = GeneratedArtifact(
                    asset_id=asset.asset_id,
                    issue_id=issue.issue_id,
                    artifact_type=artifact_type,
                    generation_status="COMPLETE",
                    storage_location=str(path),
                )
                db.add(artifact)
            issue.fix_recommendation = "Captions generated. Review and approve."
            issue.confidence_score = 0.85
