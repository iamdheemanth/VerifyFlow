"""add durable run queue fields

Revision ID: f2b9c8d1e0a3
Revises: e7a1b0c9d2f4
Create Date: 2026-04-25 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2b9c8d1e0a3"
down_revision: Union[str, None] = "e7a1b0c9d2f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NEW_STATUS_CHECK = (
    "status IN ('pending', 'queued', 'planning', 'executing', 'verifying', "
    "'completed', 'failed', 'needs_review')"
)
OLD_STATUS_CHECK = "status IN ('pending', 'planning', 'executing', 'completed', 'failed')"


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def _queue_columns() -> list[sa.Column]:
    return [
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_owner", sa.String(length=128), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_worker_error", sa.Text(), nullable=True),
    ]


def _add_queue_columns_batch(batch_op) -> None:
    for column in _queue_columns():
        batch_op.add_column(column)


def _add_queue_columns() -> None:
    for column in _queue_columns():
        op.add_column("runs", column)


def _drop_queue_columns(batch_op) -> None:
    batch_op.drop_column("last_worker_error")
    batch_op.drop_column("execution_attempts")
    batch_op.drop_column("lease_expires_at")
    batch_op.drop_column("lease_owner")
    batch_op.drop_column("finished_at")
    batch_op.drop_column("started_at")
    batch_op.drop_column("queued_at")


def _drop_queue_columns_direct() -> None:
    for column_name in [
        "last_worker_error",
        "execution_attempts",
        "lease_expires_at",
        "lease_owner",
        "finished_at",
        "started_at",
        "queued_at",
    ]:
        op.drop_column("runs", column_name)


def upgrade() -> None:
    if _is_sqlite():
        with op.batch_alter_table("runs", recreate="always") as batch_op:
            batch_op.drop_constraint("ck_runs_status", type_="check")
            _add_queue_columns_batch(batch_op)
            batch_op.create_check_constraint("ck_runs_status", NEW_STATUS_CHECK)
    else:
        op.drop_constraint("ck_runs_status", "runs", type_="check")
        _add_queue_columns()
        op.create_check_constraint("ck_runs_status", "runs", NEW_STATUS_CHECK)

    op.execute(
        """
        UPDATE runs
        SET status = 'queued',
            queued_at = COALESCE(queued_at, created_at),
            lease_owner = NULL,
            lease_expires_at = NULL
        WHERE status = 'pending'
        """
    )
    op.create_index("ix_runs_status_queued_at", "runs", ["status", "queued_at"])
    op.create_index("ix_runs_lease_expires_at", "runs", ["lease_expires_at"])


def downgrade() -> None:
    op.drop_index("ix_runs_lease_expires_at", table_name="runs")
    op.drop_index("ix_runs_status_queued_at", table_name="runs")
    op.execute("UPDATE runs SET status = 'pending' WHERE status = 'queued'")
    op.execute("UPDATE runs SET status = 'executing' WHERE status = 'verifying'")
    op.execute("UPDATE runs SET status = 'failed' WHERE status = 'needs_review'")

    if _is_sqlite():
        with op.batch_alter_table("runs", recreate="always") as batch_op:
            batch_op.drop_constraint("ck_runs_status", type_="check")
            batch_op.create_check_constraint("ck_runs_status", OLD_STATUS_CHECK)
            _drop_queue_columns(batch_op)
    else:
        op.drop_constraint("ck_runs_status", "runs", type_="check")
        op.create_check_constraint("ck_runs_status", "runs", OLD_STATUS_CHECK)
        _drop_queue_columns_direct()
