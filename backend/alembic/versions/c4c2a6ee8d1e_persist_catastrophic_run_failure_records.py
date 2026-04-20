"""persist catastrophic run failure records

Revision ID: c4c2a6ee8d1e
Revises: d3f532773223
Create Date: 2026-04-20 15:05:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c4c2a6ee8d1e"
down_revision: Union[str, None] = "d3f532773223"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column(
            "failure_record",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("runs", "failure_record")
