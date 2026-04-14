"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accessibility_asset",
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", sa.String(255), nullable=True),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("source_type", sa.String(10), nullable=False),
        sa.Column("source_location", sa.String(1024), nullable=False),
        sa.Column("file_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("normalized_content_ref", sa.String(1024), nullable=True),
        sa.Column("processing_status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("asset_id"),
    )
    op.create_index("ix_accessibility_asset_course_id", "accessibility_asset", ["course_id"])

    op.create_table(
        "accessibility_issue",
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issue_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("location_in_asset", postgresql.JSONB(), nullable=True),
        sa.Column("fix_recommendation", sa.Text(), nullable=True),
        sa.Column("auto_fixable", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("review_status", sa.String(10), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["accessibility_asset.asset_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("issue_id"),
    )
    op.create_index("ix_accessibility_issue_asset_id", "accessibility_issue", ["asset_id"])
    op.create_index("ix_accessibility_issue_issue_type", "accessibility_issue", ["issue_type"])
    op.create_index("ix_accessibility_issue_severity", "accessibility_issue", ["severity"])
    op.create_index("ix_accessibility_issue_review_status", "accessibility_issue", ["review_status"])
    op.create_index(
        "ix_accessibility_issue_location_gin",
        "accessibility_issue",
        ["location_in_asset"],
        postgresql_using="gin",
    )

    op.create_table(
        "generated_artifact",
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("artifact_type", sa.String(30), nullable=False),
        sa.Column("generation_status", sa.String(10), nullable=False, server_default="PENDING"),
        sa.Column("storage_location", sa.String(1024), nullable=True),
        sa.Column("content_snapshot", sa.Text(), nullable=True),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["accessibility_asset.asset_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["issue_id"], ["accessibility_issue.issue_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("artifact_id"),
    )
    op.create_index("ix_generated_artifact_asset_id", "generated_artifact", ["asset_id"])
    op.create_index("ix_generated_artifact_issue_id", "generated_artifact", ["issue_id"])
    op.create_index("ix_generated_artifact_artifact_type", "generated_artifact", ["artifact_type"])

    op.create_table(
        "audit_event",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("before_state", postgresql.JSONB(), nullable=True),
        sa.Column("after_state", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["accessibility_asset.asset_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_audit_event_action", "audit_event", ["action"])
    op.create_index("ix_audit_event_asset_id", "audit_event", ["asset_id"])
    op.create_index("ix_audit_event_timestamp", "audit_event", ["timestamp"])


def downgrade() -> None:
    op.drop_table("audit_event")
    op.drop_table("generated_artifact")
    op.drop_table("accessibility_issue")
    op.drop_table("accessibility_asset")
