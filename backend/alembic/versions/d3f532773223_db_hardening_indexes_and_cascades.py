"""db hardening indexes and cascades

Revision ID: d3f532773223
Revises: a7a25d8f0c31
Create Date: 2026-04-20 14:20:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d3f532773223"
down_revision: Union[str, None] = "a7a25d8f0c31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_column(table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in _inspector().get_columns(table_name))


def _has_index(table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in _inspector().get_indexes(table_name))


def _has_unique_constraint(table_name: str, constraint_name: str) -> bool:
    return any(
        constraint["name"] == constraint_name
        for constraint in _inspector().get_unique_constraints(table_name)
    )


def _find_foreign_key(table_name: str, constrained_columns: list[str], referred_table: str):
    for foreign_key in _inspector().get_foreign_keys(table_name):
        if foreign_key["constrained_columns"] == constrained_columns and foreign_key["referred_table"] == referred_table:
            return foreign_key
    return None


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def _ensure_no_duplicates(table_name: str, columns: list[str], constraint_name: str) -> None:
    bind = op.get_bind()
    table = sa.table(table_name, *[sa.column(column) for column in columns])
    duplicate_query = (
        sa.select(*[table.c[column] for column in columns], sa.func.count().label("row_count"))
        .group_by(*[table.c[column] for column in columns])
        .having(sa.func.count() > 1)
        .limit(1)
    )
    duplicate_row = bind.execute(duplicate_query).first()
    if duplicate_row is not None:
        joined_columns = ", ".join(columns)
        raise RuntimeError(
            f"Cannot create {constraint_name}: duplicate rows exist in {table_name} for ({joined_columns})."
        )


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    if not _has_index(table_name, index_name):
        op.create_index(index_name, table_name, columns)


def upgrade() -> None:
    if not _has_column("reviewer_decisions", "reviewer_key"):
        op.add_column("reviewer_decisions", sa.Column("reviewer_key", sa.String(length=128), nullable=True))
    if not _has_column("reviewer_decisions", "reviewer_display_name"):
        op.add_column("reviewer_decisions", sa.Column("reviewer_display_name", sa.String(length=128), nullable=True))

    bind = op.get_bind()
    if _has_column("reviewer_decisions", "reviewer_name"):
        bind.execute(
            sa.text(
                """
                UPDATE reviewer_decisions
                SET reviewer_display_name = reviewer_name
                WHERE reviewer_display_name IS NULL AND reviewer_name IS NOT NULL
                """
            )
        )

    if not _is_sqlite():
        _ensure_no_duplicates("tasks", ["run_id", "index"], "uq_tasks_run_id_index")
        if not _has_unique_constraint("tasks", "uq_tasks_run_id_index"):
            op.create_unique_constraint("uq_tasks_run_id_index", "tasks", ["run_id", "index"])

    if not _is_sqlite():
        _ensure_no_duplicates(
            "task_attempts",
            ["task_id", "attempt_index"],
            "uq_task_attempts_task_id_attempt_index",
        )
        if not _has_unique_constraint("task_attempts", "uq_task_attempts_task_id_attempt_index"):
            op.create_unique_constraint(
                "uq_task_attempts_task_id_attempt_index",
                "task_attempts",
                ["task_id", "attempt_index"],
            )

    _create_index_if_missing("ix_benchmark_cases_suite_id", "benchmark_cases", ["suite_id"])
    _create_index_if_missing("ix_runs_status_created_at", "runs", ["status", "created_at"])
    _create_index_if_missing("ix_runs_kind_created_at", "runs", ["kind", "created_at"])
    _create_index_if_missing("ix_runs_executor_config_id", "runs", ["executor_config_id"])
    _create_index_if_missing("ix_runs_judge_config_id", "runs", ["judge_config_id"])
    _create_index_if_missing("ix_runs_benchmark_suite_id", "runs", ["benchmark_suite_id"])
    _create_index_if_missing("ix_runs_benchmark_case_id", "runs", ["benchmark_case_id"])
    _create_index_if_missing("ix_tasks_run_id_status", "tasks", ["run_id", "status"])
    _create_index_if_missing("ix_tasks_run_id_index", "tasks", ["run_id", "index"])
    _create_index_if_missing("ix_task_attempts_run_id_created_at", "task_attempts", ["run_id", "created_at"])
    _create_index_if_missing("ix_task_attempts_task_id_created_at", "task_attempts", ["task_id", "created_at"])
    _create_index_if_missing("ix_escalations_status_created_at", "escalations", ["status", "created_at"])
    _create_index_if_missing("ix_escalations_run_id_status", "escalations", ["run_id", "status"])
    _create_index_if_missing("ix_escalations_task_id_status", "escalations", ["task_id", "status"])
    _create_index_if_missing(
        "ix_reviewer_decisions_escalation_id_created_at",
        "reviewer_decisions",
        ["escalation_id", "created_at"],
    )
    _create_index_if_missing(
        "ix_reviewer_decisions_run_id_created_at",
        "reviewer_decisions",
        ["run_id", "created_at"],
    )
    _create_index_if_missing(
        "ix_reviewer_decisions_task_id_created_at",
        "reviewer_decisions",
        ["task_id", "created_at"],
    )
    _create_index_if_missing("ix_ledger_entries_run_id_created_at", "ledger_entries", ["run_id", "created_at"])
    _create_index_if_missing("ix_ledger_entries_task_id_created_at", "ledger_entries", ["task_id", "created_at"])
    _create_index_if_missing("ix_ledger_entries_attempt_id", "ledger_entries", ["attempt_id"])

    if not _is_sqlite():
        ledger_run_fk = _find_foreign_key("ledger_entries", ["run_id"], "runs")
        current_ondelete = (ledger_run_fk or {}).get("options", {}).get("ondelete")
        if current_ondelete != "CASCADE":
            if ledger_run_fk and ledger_run_fk.get("name"):
                op.drop_constraint(ledger_run_fk["name"], "ledger_entries", type_="foreignkey")
            op.create_foreign_key(
                "fk_ledger_entries_run_id_cascade",
                "ledger_entries",
                "runs",
                ["run_id"],
                ["id"],
                ondelete="CASCADE",
            )


def downgrade() -> None:
    ledger_run_fk = _find_foreign_key("ledger_entries", ["run_id"], "runs")
    if ledger_run_fk and ledger_run_fk.get("name") == "fk_ledger_entries_run_id_cascade":
        op.drop_constraint("fk_ledger_entries_run_id_cascade", "ledger_entries", type_="foreignkey")
        op.create_foreign_key(
            "ledger_entries_run_id_fkey",
            "ledger_entries",
            "runs",
            ["run_id"],
            ["id"],
        )

    for table_name, index_name in [
        ("ledger_entries", "ix_ledger_entries_attempt_id"),
        ("ledger_entries", "ix_ledger_entries_task_id_created_at"),
        ("ledger_entries", "ix_ledger_entries_run_id_created_at"),
        ("reviewer_decisions", "ix_reviewer_decisions_task_id_created_at"),
        ("reviewer_decisions", "ix_reviewer_decisions_run_id_created_at"),
        ("reviewer_decisions", "ix_reviewer_decisions_escalation_id_created_at"),
        ("escalations", "ix_escalations_task_id_status"),
        ("escalations", "ix_escalations_run_id_status"),
        ("escalations", "ix_escalations_status_created_at"),
        ("task_attempts", "ix_task_attempts_task_id_created_at"),
        ("task_attempts", "ix_task_attempts_run_id_created_at"),
        ("tasks", "ix_tasks_run_id_index"),
        ("tasks", "ix_tasks_run_id_status"),
        ("runs", "ix_runs_benchmark_case_id"),
        ("runs", "ix_runs_benchmark_suite_id"),
        ("runs", "ix_runs_judge_config_id"),
        ("runs", "ix_runs_executor_config_id"),
        ("runs", "ix_runs_kind_created_at"),
        ("runs", "ix_runs_status_created_at"),
        ("benchmark_cases", "ix_benchmark_cases_suite_id"),
    ]:
        if _has_index(table_name, index_name):
            op.drop_index(index_name, table_name=table_name)

    if _has_unique_constraint("task_attempts", "uq_task_attempts_task_id_attempt_index"):
        op.drop_constraint("uq_task_attempts_task_id_attempt_index", "task_attempts", type_="unique")
    if _has_unique_constraint("tasks", "uq_tasks_run_id_index"):
        op.drop_constraint("uq_tasks_run_id_index", "tasks", type_="unique")

    if _has_column("reviewer_decisions", "reviewer_display_name"):
        op.drop_column("reviewer_decisions", "reviewer_display_name")
    if _has_column("reviewer_decisions", "reviewer_key"):
        op.drop_column("reviewer_decisions", "reviewer_key")
