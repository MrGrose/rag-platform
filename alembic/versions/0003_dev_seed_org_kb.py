import sqlalchemy as sa
from alembic import op

revision = "0003_dev_seed_org_kb"
down_revision = "0002_org_kb"
branch_labels = None
depends_on = None

DEFAULT_ORG_ID = "00000000-0000-4000-8000-000000000001"
DEFAULT_KB_ID = "00000000-0000-4000-8000-000000000002"


def upgrade() -> None:
    organizations = sa.table(
        "organizations",
        sa.column("id", sa.UUID()),
        sa.column("name", sa.String()),
    )
    knowledge_bases = sa.table(
        "knowledge_bases",
        sa.column("id", sa.UUID()),
        sa.column("organization_id", sa.UUID()),
        sa.column("name", sa.String()),
    )
    bind = op.get_bind()
    org_exists = bind.execute(
        sa.select(sa.literal(1))
        .select_from(organizations)
        .where(
            organizations.c.id == DEFAULT_ORG_ID,
        ),
    ).first()
    if org_exists is None:
        op.execute(
            organizations.insert().values(id=DEFAULT_ORG_ID, name="default"),
        )
    kb_exists = bind.execute(
        sa.select(sa.literal(1))
        .select_from(knowledge_bases)
        .where(
            knowledge_bases.c.id == DEFAULT_KB_ID,
        ),
    ).first()
    if kb_exists is None:
        op.execute(
            knowledge_bases.insert().values(
                id=DEFAULT_KB_ID,
                organization_id=DEFAULT_ORG_ID,
                name="default",
            ),
        )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM knowledge_bases WHERE id = :kid").bindparams(kid=DEFAULT_KB_ID),
    )
    op.execute(
        sa.text("DELETE FROM organizations WHERE id = :oid").bindparams(oid=DEFAULT_ORG_ID),
    )
