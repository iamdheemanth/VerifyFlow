from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8c7d6e5f4a3"
down_revision: Union[str, None] = "f2b9c8d1e0a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("benchmark_cases", sa.Column("owner_subject", sa.String(length=255), nullable=True))
    op.add_column("benchmark_cases", sa.Column("owner_email", sa.String(length=255), nullable=True))
    op.create_index(
        "ix_benchmark_cases_owner_subject_suite_id",
        "benchmark_cases",
        ["owner_subject", "suite_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_benchmark_cases_owner_subject_suite_id", table_name="benchmark_cases")
    op.drop_column("benchmark_cases", "owner_email")
    op.drop_column("benchmark_cases", "owner_subject")
