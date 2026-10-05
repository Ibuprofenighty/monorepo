"""0002: scope idempotency records by principal subject.

Primary key becomes (subject, key). Existing rows carry no subject and cannot be
attributed to a principal; they are a 24h replay cache, so they are cleared
rather than replayed across principals.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_idempotency_scope"
down_revision = "0001_catalog_resources"
branch_labels = None
depends_on = None

TABLE = "catalog_idempotency_keys"
PK = "catalog_idempotency_keys_pkey"


def upgrade() -> None:
    op.execute(sa.text(f"DELETE FROM {TABLE}"))
    op.add_column(TABLE, sa.Column("subject", sa.String(255), nullable=False))
    op.drop_constraint(PK, TABLE, type_="primary")
    op.create_primary_key(PK, TABLE, ["subject", "key"])


def downgrade() -> None:
    op.execute(sa.text(f"DELETE FROM {TABLE}"))
    op.drop_constraint(PK, TABLE, type_="primary")
    op.drop_column(TABLE, "subject")
    op.create_primary_key(PK, TABLE, ["key"])
