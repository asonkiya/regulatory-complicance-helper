import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.issue import AccessibilityIssue
from app.schemas.issue import IssueListResponse, IssueResponse, IssueUpdateRequest

router = APIRouter()

VALID_REVIEW_STATUSES = {"PENDING", "APPROVED", "REJECTED", "SKIPPED"}


@router.get("/assets/{asset_id}/issues", response_model=IssueListResponse)
def list_issues(
    asset_id: uuid.UUID,
    severity: str | None = None,
    review_status: str | None = None,
    db: Session = Depends(get_db),
) -> IssueListResponse:
    query = select(AccessibilityIssue).where(AccessibilityIssue.asset_id == asset_id)

    if severity:
        query = query.where(AccessibilityIssue.severity == severity.upper())
    if review_status:
        query = query.where(AccessibilityIssue.review_status == review_status.upper())

    # Sort: CRITICAL first, then SERIOUS, MODERATE, MINOR
    severity_order = {"CRITICAL": 0, "SERIOUS": 1, "MODERATE": 2, "MINOR": 3}
    issues = db.scalars(query).all()
    issues = sorted(issues, key=lambda i: severity_order.get(i.severity, 99))

    return IssueListResponse(
        issues=[IssueResponse.model_validate(i) for i in issues],
        total=len(issues),
    )


@router.patch("/issues/{issue_id}", response_model=IssueResponse)
def update_issue(
    issue_id: uuid.UUID,
    body: IssueUpdateRequest,
    db: Session = Depends(get_db),
) -> IssueResponse:
    issue = db.get(AccessibilityIssue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    if body.review_status is not None:
        if body.review_status.upper() not in VALID_REVIEW_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid review_status. Must be one of: {VALID_REVIEW_STATUSES}",
            )
        issue.review_status = body.review_status.upper()

    if body.fix_recommendation is not None:
        issue.fix_recommendation = body.fix_recommendation

    db.commit()
    db.refresh(issue)
    return IssueResponse.model_validate(issue)
