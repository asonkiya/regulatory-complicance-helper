import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GeneratedArtifact(Base):
    __tablename__ = "generated_artifact"

    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accessibility_asset.asset_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    issue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accessibility_issue.issue_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # ALT_TEXT | TRANSCRIPT | CAPTIONS_VTT | CAPTIONS_SRT | TAGGED_PDF | ACCESSIBILITY_REPORT
    artifact_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    # PENDING | COMPLETE | FAILED
    generation_status: Mapped[str] = mapped_column(String(10), default="PENDING", nullable=False)
    storage_location: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # Short content stored inline (alt text, brief transcript snippets)
    content_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    asset: Mapped["AccessibilityAsset"] = relationship(  # noqa: F821
        "AccessibilityAsset", back_populates="artifacts"
    )
    issue: Mapped["AccessibilityIssue | None"] = relationship(  # noqa: F821
        "AccessibilityIssue", back_populates="artifacts"
    )
