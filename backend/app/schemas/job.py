from pydantic import BaseModel


class JobStatusResponse(BaseModel):
    task_id: str
    asset_id: str | None
    state: str  # PENDING | STARTED | SUCCESS | FAILURE | RETRY
    current_stage: str | None  # NORMALIZING | CHECKING | REMEDIATING | OUTPUTTING | COMPLETE
    progress_percent: int | None
    error: str | None
