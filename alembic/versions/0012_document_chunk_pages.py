"""Store the page number a chunk came from."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_document_chunk_pages"
down_revision: str | Sequence[str] | None = "0011_embedding_dimension_1024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("document_chunks", sa.Column("page", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_chunks", "page")
