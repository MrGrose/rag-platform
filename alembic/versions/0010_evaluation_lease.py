"""evaluation lease columns

Revision ID: 0010_evaluation_lease
Revises: 0009_outbox_events
Create Date: 2026-03-31
"""

import sqlalchemy as sa
from alembic import op

revision = "0010_evaluation_lease"
down_revision = "0009_outbox_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "evaluations",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "evaluations",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "evaluations",
        sa.Column("worker_claim_token", sa.String(64), nullable=True),
    )
    op.create_index("ix_evaluations_stale_lease", "evaluations", ["lease_expires_at"])


def downgrade() -> None:
    op.drop_index("ix_evaluations_stale_lease", table_name="evaluations")
    op.drop_column("evaluations", "worker_claim_token")
    op.drop_column("evaluations", "lease_expires_at")
    op.drop_column("evaluations", "processing_started_at")
