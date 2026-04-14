import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AccessibilityAsset(Base):
    __tablename__ = "accessibility_asset"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    # PPTX | PDF | MP4
    source_type: Mapped[str] = mapped_column(String(10), nullable=False)
    source_location: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    normalized_content_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # PENDING | NORMALIZING | CHECKING | REMEDIATING | OUTPUTTING | COMPLETE | FAILED
    processing_status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    issues: Mapped[list["AccessibilityIssue"]] = relationship(  # noqa: F821
        "AccessibilityIssue", back_populates="asset", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list["GeneratedArtifact"]] = relationship(  # noqa: F821
        "GeneratedArtifact", back_populates="asset", cascade="all, delete-orphan"
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(  # noqa: F821
        "AuditEvent", back_populates="asset"
    )
