"""
Calculates an accessibility score (0-100) for an asset based on
its unresolved issues.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import AccessibilityAsset
from app.models.issue import AccessibilityIssue

# Issue weight: how many points are deducted per unresolved issue of each type
_ISSUE_WEIGHTS: dict[str, int] = {
    "MISSING_ALT_TEXT": 20,
    "MISSING_CAPTIONS": 20,
    "UNTAGGED_PDF": 15,
    "MISSING_SLIDE_TITLE": 10,
    "LOW_CONTRAST": 10,
    "MISSING_HEADING_STRUCTURE": 8,
    "MISSING_LINK_TEXT": 8,
    "MISSING_TABLE_HEADERS": 8,
    "INADEQUATE_ALT_TEXT": 5,
    "MISSING_LANGUAGE": 5,
    "MISSING_DOCUMENT_TITLE": 6,
    "LOW_OCR_CONFIDENCE": 3,
    "CONTRAST_UNVERIFIABLE": 1,
}

# WCAG 2.0 success criteria mapping
_WCAG_MAP: dict[str, str] = {
    "MISSING_ALT_TEXT": "1.1.1 Non-text Content (Level A)",
    "INADEQUATE_ALT_TEXT": "1.1.1 Non-text Content (Level A)",
    "MISSING_CAPTIONS": "1.2.2 Captions (Prerecorded) (Level A)",
    "LOW_CONTRAST": "1.4.3 Contrast Minimum (Level AA)",
    "CONTRAST_UNVERIFIABLE": "1.4.3 Contrast Minimum (Level AA)",
    "UNTAGGED_PDF": "1.3.1 Info and Relationships (Level A)",
    "MISSING_LANGUAGE": "3.1.1 Language of Page (Level A)",
    "MISSING_SLIDE_TITLE": "2.4.2 Page Titled (Level A)",
    "MISSING_HEADING_STRUCTURE": "1.3.1 Info and Relationships / 2.4.6 Headings and Labels (Level A/AA)",
    "MISSING_LINK_TEXT": "2.4.4 Link Purpose (Level A)",
    "MISSING_TABLE_HEADERS": "1.3.1 Info and Relationships (Level A)",
    "MISSING_DOCUMENT_TITLE": "2.4.2 Page Titled (Level A)",
    "LOW_OCR_CONFIDENCE": "1.1.1 Non-text Content (Level A)",
}


def calculate_score(db: Session, asset: AccessibilityAsset) -> dict:
    issues = db.scalars(
        select(AccessibilityIssue).where(AccessibilityIssue.asset_id == asset.asset_id)
    ).all()

    total_deduction = 0
    issues_by_severity: dict[str, int] = {
        "CRITICAL": 0, "SERIOUS": 0, "MODERATE": 0, "MINOR": 0
    }
    auto_fixed_count = 0
    pending_review_count = 0
    wcag_criteria: dict[str, list[str]] = {}

    for issue in issues:
        is_resolved = issue.review_status in ("APPROVED", "SKIPPED")
        if not is_resolved:
            weight = _ISSUE_WEIGHTS.get(issue.issue_type, 2)
            total_deduction += weight
            issues_by_severity[issue.severity] = issues_by_severity.get(issue.severity, 0) + 1

        if issue.review_status == "APPROVED":
            auto_fixed_count += 1
        elif issue.review_status == "PENDING":
            pending_review_count += 1

        criterion = _WCAG_MAP.get(issue.issue_type)
        if criterion:
            if criterion not in wcag_criteria:
                wcag_criteria[criterion] = []
            wcag_criteria[criterion].append(issue.issue_type)

    score = max(0, 100 - total_deduction)

    return {
        "asset_id": str(asset.asset_id),
        "score": score,
        "total_issues": len(issues),
        "issues_by_severity": issues_by_severity,
        "auto_fixed_count": auto_fixed_count,
        "pending_review_count": pending_review_count,
        "wcag_criteria_map": wcag_criteria,
    }
