import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, Boolean, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AccessibilityIssue(Base):
    __tablename__ = "accessibility_issue"

    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accessibility_asset.asset_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # MISSING_ALT_TEXT | INADEQUATE_ALT_TEXT | MISSING_SLIDE_TITLE | LOW_CONTRAST |
    # CONTRAST_UNVERIFIABLE | UNTAGGED_PDF | MISSING_LANGUAGE | MISSING_CAPTIONS |
    # MISSING_HEADING_STRUCTURE | LOW_OCR_CONFIDENCE
    issue_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # CRITICAL | SERIOUS | MODERATE | MINOR
    severity: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    # e.g. {"slide": 3, "element_id": "img_1"} or {"page": 5, "bbox": [...]}
    location_in_asset: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fix_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_fixable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # PENDING | APPROVED | REJECTED | SKIPPED
    review_status: Mapped[str] = mapped_column(String(10), default="PENDING", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    asset: Mapped["AccessibilityAsset"] = relationship(  # noqa: F821
        "AccessibilityAsset", back_populates="issues"
    )
    artifacts: Mapped[list["GeneratedArtifact"]] = relationship(  # noqa: F821
        "GeneratedArtifact", back_populates="issue"
    )
