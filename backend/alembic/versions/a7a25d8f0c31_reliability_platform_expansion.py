"""reliability platform expansion

Revision ID: a7a25d8f0c31
Revises: 4e4263e2402a
Create Date: 2026-04-18 20:55:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a7a25d8f0c31"
down_revision: Union[str, None] = "4e4263e2402a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _utc_now_default():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.text("CURRENT_TIMESTAMP")
    return sa.text("TIMEZONE('utc', now())")


def _json_array_default():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.text("'[]'")
    return sa.text("'[]'::jsonb")


def _json_type():
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def upgrade() -> None:
    op.create_table(
        "model_prompt_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("prompt_template", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False, server_default="v1"),
        sa.Column("config_metadata", _json_type(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=_utc_now_default(),
        ),
        sa.CheckConstraint(
            "role IN ('executor', 'judge')",
            name="ck_model_prompt_configs_role",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "benchmark_suites",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=_utc_now_default(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "benchmark_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("suite_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("acceptance_criteria", sa.Text(), nullable=True),
        sa.Column("expected_outcome", sa.String(length=32), nullable=True),
        sa.Column("label_data", _json_type(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=_utc_now_default(),
        ),
        sa.ForeignKeyConstraint(["suite_id"], ["benchmark_suites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column("runs", sa.Column("kind", sa.String(length=32), nullable=False, server_default="standard"))
    op.add_column("runs", sa.Column("latest_confidence", sa.Float(), nullable=True))
    op.add_column("runs", sa.Column("executor_config_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("runs", sa.Column("judge_config_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("runs", sa.Column("benchmark_suite_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("runs", sa.Column("benchmark_case_id", postgresql.UUID(as_uuid=True), nullable=True))
    if not _is_sqlite():
        op.create_check_constraint("ck_runs_kind", "runs", "kind IN ('standard', 'benchmark')")
        op.create_foreign_key(
            "fk_runs_executor_config_id",
            "runs",
            "model_prompt_configs",
            ["executor_config_id"],
            ["id"],
        )
        op.create_foreign_key(
            "fk_runs_judge_config_id",
            "runs",
            "model_prompt_configs",
            ["judge_config_id"],
            ["id"],
        )
        op.create_foreign_key(
            "fk_runs_benchmark_suite_id",
            "runs",
            "benchmark_suites",
            ["benchmark_suite_id"],
            ["id"],
        )
        op.create_foreign_key(
            "fk_runs_benchmark_case_id",
            "runs",
            "benchmark_cases",
            ["benchmark_case_id"],
            ["id"],
        )

    op.create_table(
        "task_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("tool_params", _json_type(), nullable=False),
        sa.Column("action_claim", _json_type(), nullable=True),
        sa.Column("verification_payload", _json_type(), nullable=True),
        sa.Column("execution_steps", _json_type(), nullable=False, server_default=_json_array_default()),
        sa.Column("tool_calls", _json_type(), nullable=False, server_default=_json_array_default()),
        sa.Column("claimed_success", sa.Boolean(), nullable=True),
        sa.Column("verification_method", sa.String(length=32), nullable=True),
        sa.Column("final_confidence", sa.Float(), nullable=True),
        sa.Column("executor_latency_ms", sa.Float(), nullable=True),
        sa.Column("verifier_latency_ms", sa.Float(), nullable=True),
        sa.Column("total_latency_ms", sa.Float(), nullable=True),
        sa.Column("token_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_output", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=_utc_now_default(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=_utc_now_default(),
        ),
        sa.CheckConstraint("attempt_index >= 0", name="ck_task_attempts_attempt_index"),
        sa.CheckConstraint(
            "verification_method IS NULL OR verification_method IN ('deterministic', 'llm_judge', 'hybrid')",
            name="ck_task_attempts_verification_method",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column("ledger_entries", sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=True))
    if not _is_sqlite():
        op.create_foreign_key(
            "fk_ledger_entries_attempt_id",
            "ledger_entries",
            "task_attempts",
            ["attempt_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_table(
        "run_telemetry",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_executor_latency_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_verifier_latency_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_task_latency_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_token_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_token_output", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_token_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_estimated_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_tool_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deterministic_verifications", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_judge_verifications", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hybrid_verifications", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("average_confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=_utc_now_default(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=_utc_now_default(),
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )

    op.create_table(
        "escalations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending_review"),
        sa.Column("failure_reason", sa.Text(), nullable=False),
        sa.Column("evidence_bundle", _json_type(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=_utc_now_default(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending_review', 'approved', 'rejected', 'sent_back')",
            name="ck_escalations_status",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "reviewer_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("escalation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_name", sa.String(length=128), nullable=True),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=_utc_now_default(),
        ),
        sa.CheckConstraint(
            "decision IN ('approve', 'reject', 'send_back')",
            name="ck_reviewer_decisions_decision",
        ),
        sa.ForeignKeyConstraint(["escalation_id"], ["escalations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("reviewer_decisions")
    op.drop_table("escalations")
    op.drop_table("run_telemetry")
    op.drop_constraint("fk_ledger_entries_attempt_id", "ledger_entries", type_="foreignkey")
    op.drop_column("ledger_entries", "attempt_id")
    op.drop_table("task_attempts")
    op.drop_constraint("fk_runs_benchmark_case_id", "runs", type_="foreignkey")
    op.drop_constraint("fk_runs_benchmark_suite_id", "runs", type_="foreignkey")
    op.drop_constraint("fk_runs_judge_config_id", "runs", type_="foreignkey")
    op.drop_constraint("fk_runs_executor_config_id", "runs", type_="foreignkey")
    op.drop_constraint("ck_runs_kind", "runs", type_="check")
    op.drop_column("runs", "benchmark_case_id")
    op.drop_column("runs", "benchmark_suite_id")
    op.drop_column("runs", "judge_config_id")
    op.drop_column("runs", "executor_config_id")
    op.drop_column("runs", "latest_confidence")
    op.drop_column("runs", "kind")
    op.drop_table("benchmark_cases")
    op.drop_table("benchmark_suites")
    op.drop_table("model_prompt_configs")
