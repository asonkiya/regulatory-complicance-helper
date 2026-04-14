"""
Output task: generates the accessibility score report and tagged PDF.
Runs on the default queue after remediation completes.
"""
import logging

from app.tasks.celery_app import celery_app
from app.tasks.utils import get_db_session, set_asset_status, set_stage_in_redis

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.output_task.generate_outputs", queue="default")
def generate_outputs(self, asset_id: str) -> str:
    """Generate tagged PDF, score report, and finalize asset. Returns asset_id."""
    set_stage_in_redis(asset_id, "OUTPUTTING")
    self.update_state(state="STARTED", meta={"stage": "OUTPUTTING", "asset_id": asset_id})

    with get_db_session() as db:
        from app.models.asset import AccessibilityAsset

        asset = db.get(AccessibilityAsset, asset_id)
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")

        set_asset_status(db, asset, "OUTPUTTING")

        try:
            # Generate accessibility score report
            from app.processing.output_generators.score_calculator import calculate_score

            score_report = calculate_score(db, asset)

            from app.models.artifact import GeneratedArtifact
            import json

            from app.services.storage_service import get_asset_dir

            report_path = get_asset_dir(asset_id) / "accessibility_report.json"
            with open(report_path, "w") as f:
                json.dump(score_report, f, indent=2)

            db.add(
                GeneratedArtifact(
                    asset_id=asset.asset_id,
                    artifact_type="ACCESSIBILITY_REPORT",
                    generation_status="COMPLETE",
                    storage_location=str(report_path),
                    content_snapshot=str(score_report.get("score", 0)),
                )
            )

            # Generate tagged PDF if source is PDF
            if asset.source_type == "PDF":
                from app.processing.output_generators.tagged_pdf_generator import generate_tagged_pdf

                tagged_path = generate_tagged_pdf(db, asset)
                if tagged_path:
                    db.add(
                        GeneratedArtifact(
                            asset_id=asset.asset_id,
                            artifact_type="TAGGED_PDF",
                            generation_status="COMPLETE",
                            storage_location=str(tagged_path),
                        )
                    )

            set_asset_status(db, asset, "COMPLETE")
            db.commit()

            set_stage_in_redis(asset_id, "COMPLETE")
            self.update_state(state="SUCCESS", meta={"stage": "COMPLETE", "asset_id": asset_id})

            logger.info("Output generation complete for asset %s", asset_id)

        except Exception as exc:
            set_asset_status(db, asset, "FAILED")
            logger.exception("Output generation failed for asset %s", asset_id)
            raise self.retry(exc=exc, countdown=30, max_retries=2) from exc

    return asset_id
