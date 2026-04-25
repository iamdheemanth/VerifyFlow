"""add run ownership fields

Revision ID: e7a1b0c9d2f4
Revises: c4c2a6ee8d1e
Create Date: 2026-04-24 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e7a1b0c9d2f4"
down_revision: Union[str, None] = "c4c2a6ee8d1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("owner_subject", sa.String(length=255), nullable=True))
    op.add_column("runs", sa.Column("owner_email", sa.String(length=255), nullable=True))
    op.create_index("ix_runs_owner_subject_created_at", "runs", ["owner_subject", "created_at"])
    op.create_index("ix_runs_owner_subject_status_created_at", "runs", ["owner_subject", "status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_runs_owner_subject_status_created_at", table_name="runs")
    op.drop_index("ix_runs_owner_subject_created_at", table_name="runs")
    op.drop_column("runs", "owner_email")
    op.drop_column("runs", "owner_subject")
