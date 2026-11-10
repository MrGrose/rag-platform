"""Move chunk embeddings to the bge-m3 dimension.

Existing chunks are dropped: vectors produced by another model cannot be
reused, so the knowledge base must be re-indexed after this migration.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0011_embedding_dimension_1024"
down_revision: str | Sequence[str] | None = "0010_evaluation_lease"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("TRUNCATE TABLE retrieval_results, document_chunks RESTART IDENTITY CASCADE")
    op.drop_column("document_chunks", "embedding")
    op.add_column(
        "document_chunks",
        sa.Column("embedding", Vector(1024), nullable=False),
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.execute("TRUNCATE TABLE retrieval_results, document_chunks RESTART IDENTITY CASCADE")
    op.drop_column("document_chunks", "embedding")
    op.add_column(
        "document_chunks",
        sa.Column("embedding", Vector(8), nullable=False),
    )
