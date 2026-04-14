from fastapi import APIRouter
from celery.result import AsyncResult

from app.schemas.job import JobStatusResponse
from app.tasks.celery_app import celery_app

router = APIRouter()

# Map Celery states to a progress percentage
_STAGE_PROGRESS = {
    "NORMALIZING": 20,
    "CHECKING": 45,
    "REMEDIATING": 65,
    "OUTPUTTING": 85,
    "COMPLETE": 100,
}


@router.get("/jobs/{task_id}/status", response_model=JobStatusResponse)
def get_job_status(task_id: str) -> JobStatusResponse:
    result = AsyncResult(task_id, app=celery_app)

    # Try to get stage from task meta (set by each pipeline task)
    meta = result.info if isinstance(result.info, dict) else {}
    current_stage = meta.get("stage")
    asset_id = meta.get("asset_id")
    error = None

    if result.state == "FAILURE":
        error = str(result.info) if result.info else "Unknown error"
        current_stage = current_stage or "FAILED"

    progress = _STAGE_PROGRESS.get(current_stage or "", None)
    if result.state == "PENDING":
        progress = 5

    return JobStatusResponse(
        task_id=task_id,
        asset_id=asset_id,
        state=result.state,
        current_stage=current_stage,
        progress_percent=progress,
        error=error,
    )
