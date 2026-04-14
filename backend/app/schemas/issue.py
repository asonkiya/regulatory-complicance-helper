import uuid
from datetime import datetime

from pydantic import BaseModel


class IssueResponse(BaseModel):
    issue_id: uuid.UUID
    asset_id: uuid.UUID
    issue_type: str
    severity: str
    location_in_asset: dict | None
    fix_recommendation: str | None
    auto_fixable: bool
    confidence_score: float | None
    review_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class IssueUpdateRequest(BaseModel):
    review_status: str | None = None
    fix_recommendation: str | None = None


class IssueListResponse(BaseModel):
    issues: list[IssueResponse]
    total: int
