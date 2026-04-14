import uuid
from datetime import datetime

from pydantic import BaseModel


class ArtifactResponse(BaseModel):
    artifact_id: uuid.UUID
    asset_id: uuid.UUID
    issue_id: uuid.UUID | None
    artifact_type: str
    generation_status: str
    storage_location: str | None
    content_snapshot: str | None
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ArtifactApproveRequest(BaseModel):
    approved_by: str = "professor"
