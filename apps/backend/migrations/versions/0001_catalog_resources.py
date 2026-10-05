"""0001: catalog resources + idempotency keys.

Published migrations are never edited or deleted (blueprint 01 §6) —
clean up with a forward migration.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_catalog_resources"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_resources",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_table(
        "catalog_idempotency_keys",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("body_hash", sa.String(64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("catalog_idempotency_keys")
    op.drop_table("catalog_resources")
