"""
Main processing pipeline for accessibility analysis.

The pipeline is a Celery chain:
  normalize_task → check_task → remediate_task → output_task

Each task updates processing_status on the asset row and writes the current
stage to a Redis key so the /jobs/{task_id}/status endpoint can report progress.
"""
from celery import chain

from app.tasks.celery_app import celery_app
from app.tasks.normalize_task import normalize_asset
from app.tasks.check_task import check_asset
from app.tasks.remediate_task import remediate_asset
from app.tasks.output_task import generate_outputs


@celery_app.task(bind=True, name="app.tasks.pipeline.process_asset_pipeline")
def process_asset_pipeline(self, asset_id: str) -> dict:
    """
    Entry point: dispatches the full processing chain for an asset.
    Returns the asset_id so the chain passes it downstream.
    """
    pipeline = chain(
        normalize_asset.s(asset_id),
        check_asset.s(),
        remediate_asset.s(),
        generate_outputs.s(),
    )
    result = pipeline.apply_async()
    return {"asset_id": asset_id, "pipeline_id": result.id}
