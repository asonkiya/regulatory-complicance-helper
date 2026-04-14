"""
Shared issue dataclass returned by all checkers.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class IssueResult:
    issue_type: str
    severity: str
    location_in_asset: dict | None = None
    fix_recommendation: str | None = None
    auto_fixable: bool = False
    confidence_score: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)
