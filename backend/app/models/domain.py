from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


uuid_type = Uuid(as_uuid=True)
json_type = JSON().with_variant(JSONB, "postgresql")


class ModelPromptConfig(Base):
    __tablename__ = "model_prompt_configs"
    __table_args__ = (
        CheckConstraint("role IN ('executor', 'judge')", name="ck_model_prompt_configs_role"),
    )

    id: Mapped[UUID] = mapped_column(uuid_type, primary_key=True, default=uuid4)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    config_metadata: Mapped[dict[str, Any] | None] = mapped_column(json_type, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    executor_runs: Mapped[list["Run"]] = relationship(
        back_populates="executor_config",
        foreign_keys="Run.executor_config_id",
    )
    judge_runs: Mapped[list["Run"]] = relationship(
        back_populates="judge_config",
        foreign_keys="Run.judge_config_id",
    )


class BenchmarkSuite(Base):
    __tablename__ = "benchmark_suites"

    id: Mapped[UUID] = mapped_column(uuid_type, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    cases: Mapped[list["BenchmarkCase"]] = relationship(
        back_populates="suite",
        cascade="all, delete-orphan",
    )
    runs: Mapped[list["Run"]] = relationship(back_populates="benchmark_suite")


class BenchmarkCase(Base):
    __tablename__ = "benchmark_cases"
    __table_args__ = (
        Index("ix_benchmark_cases_suite_id", "suite_id"),
        Index("ix_benchmark_cases_owner_subject_suite_id", "owner_subject", "suite_id"),
    )

    id: Mapped[UUID] = mapped_column(uuid_type, primary_key=True, default=uuid4)
    owner_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    suite_id: Mapped[UUID] = mapped_column(
        uuid_type,
        ForeignKey("benchmark_suites.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    acceptance_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    label_data: Mapped[dict[str, Any] | None] = mapped_column(json_type, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    suite: Mapped["BenchmarkSuite"] = relationship(back_populates="cases")
    runs: Mapped[list["Run"]] = relationship(back_populates="benchmark_case")


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'queued', 'planning', 'executing', 'verifying', 'completed', 'failed', 'needs_review')",
            name="ck_runs_status",
        ),
        CheckConstraint("kind IN ('standard', 'benchmark')", name="ck_runs_kind"),
        Index("ix_runs_status_created_at", "status", "created_at"),
        Index("ix_runs_status_queued_at", "status", "queued_at"),
        Index("ix_runs_lease_expires_at", "lease_expires_at"),
        Index("ix_runs_kind_created_at", "kind", "created_at"),
        Index("ix_runs_executor_config_id", "executor_config_id"),
        Index("ix_runs_judge_config_id", "judge_config_id"),
        Index("ix_runs_benchmark_suite_id", "benchmark_suite_id"),
        Index("ix_runs_benchmark_case_id", "benchmark_case_id"),
        Index("ix_runs_owner_subject_created_at", "owner_subject", "created_at"),
        Index("ix_runs_owner_subject_status_created_at", "owner_subject", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(uuid_type, primary_key=True, default=uuid4)
    owner_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    acceptance_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="standard")
    latest_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    failure_record: Mapped[dict[str, Any] | None] = mapped_column(json_type, nullable=True)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_worker_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    executor_config_id: Mapped[UUID | None] = mapped_column(
        uuid_type,
        ForeignKey("model_prompt_configs.id"),
        nullable=True,
    )
    judge_config_id: Mapped[UUID | None] = mapped_column(
        uuid_type,
        ForeignKey("model_prompt_configs.id"),
        nullable=True,
    )
    benchmark_suite_id: Mapped[UUID | None] = mapped_column(
        uuid_type,
        ForeignKey("benchmark_suites.id"),
        nullable=True,
    )
    benchmark_case_id: Mapped[UUID | None] = mapped_column(
        uuid_type,
        ForeignKey("benchmark_cases.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    tasks: Mapped[list["Task"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="Task.index",
        passive_deletes=True,
    )
    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    telemetry: Mapped["RunTelemetry | None"] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        uselist=False,
        passive_deletes=True,
    )
    task_attempts: Mapped[list["TaskAttempt"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    escalations: Mapped[list["Escalation"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    reviewer_decisions: Mapped[list["ReviewerDecision"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    executor_config: Mapped["ModelPromptConfig | None"] = relationship(
        back_populates="executor_runs",
        foreign_keys=[executor_config_id],
    )
    judge_config: Mapped["ModelPromptConfig | None"] = relationship(
        back_populates="judge_runs",
        foreign_keys=[judge_config_id],
    )
    benchmark_suite: Mapped["BenchmarkSuite | None"] = relationship(back_populates="runs")
    benchmark_case: Mapped["BenchmarkCase | None"] = relationship(back_populates="runs")


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'executing', 'claimed', 'verified', 'failed', 'escalated')",
            name="ck_tasks_status",
        ),
        UniqueConstraint("run_id", "index", name="uq_tasks_run_id_index"),
        Index("ix_tasks_run_id_status", "run_id", "status"),
        Index("ix_tasks_run_id_index", "run_id", "index"),
    )

    id: Mapped[UUID] = mapped_column(uuid_type, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        uuid_type,
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    success_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_params: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    claimed_result: Mapped[dict[str, Any] | None] = mapped_column(json_type, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    run: Mapped["Run"] = relationship(back_populates="tasks")
    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    task_attempts: Mapped[list["TaskAttempt"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskAttempt.attempt_index",
        passive_deletes=True,
    )
    escalations: Mapped[list["Escalation"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    reviewer_decisions: Mapped[list["ReviewerDecision"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class TaskAttempt(Base):
    __tablename__ = "task_attempts"
    __table_args__ = (
        CheckConstraint("attempt_index >= 0", name="ck_task_attempts_attempt_index"),
        CheckConstraint(
            "verification_method IS NULL OR verification_method IN ('deterministic', 'llm_judge', 'hybrid')",
            name="ck_task_attempts_verification_method",
        ),
        UniqueConstraint("task_id", "attempt_index", name="uq_task_attempts_task_id_attempt_index"),
        Index("ix_task_attempts_run_id_created_at", "run_id", "created_at"),
        Index("ix_task_attempts_task_id_created_at", "task_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(uuid_type, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        uuid_type,
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id: Mapped[UUID] = mapped_column(
        uuid_type,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_params: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    action_claim: Mapped[dict[str, Any] | None] = mapped_column(json_type, nullable=True)
    verification_payload: Mapped[dict[str, Any] | None] = mapped_column(json_type, nullable=True)
    execution_steps: Mapped[list[dict[str, Any]]] = mapped_column(json_type, nullable=False, default=list)
    tool_calls: Mapped[list[dict[str, Any]]] = mapped_column(json_type, nullable=False, default=list)
    claimed_success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    verification_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    final_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    executor_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    verifier_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    token_input: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_output: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    run: Mapped["Run"] = relationship(back_populates="task_attempts")
    task: Mapped["Task"] = relationship(back_populates="task_attempts")
    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="attempt")


class RunTelemetry(Base):
    __tablename__ = "run_telemetry"

    id: Mapped[UUID] = mapped_column(uuid_type, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        uuid_type,
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    total_executor_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_verifier_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_task_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_token_input: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_token_output: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_token_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_tool_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deterministic_verifications: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    llm_judge_verifications: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hybrid_verifications: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    run: Mapped["Run"] = relationship(back_populates="telemetry")


class Escalation(Base):
    __tablename__ = "escalations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_review', 'approved', 'rejected', 'sent_back')",
            name="ck_escalations_status",
        ),
        Index("ix_escalations_status_created_at", "status", "created_at"),
        Index("ix_escalations_run_id_status", "run_id", "status"),
        Index("ix_escalations_task_id_status", "task_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(uuid_type, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        uuid_type,
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id: Mapped[UUID] = mapped_column(
        uuid_type,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_review")
    failure_reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_bundle: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    run: Mapped["Run"] = relationship(back_populates="escalations")
    task: Mapped["Task"] = relationship(back_populates="escalations")
    reviewer_decisions: Mapped[list["ReviewerDecision"]] = relationship(
        back_populates="escalation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ReviewerDecision(Base):
    __tablename__ = "reviewer_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approve', 'reject', 'send_back')",
            name="ck_reviewer_decisions_decision",
        ),
        Index("ix_reviewer_decisions_escalation_id_created_at", "escalation_id", "created_at"),
        Index("ix_reviewer_decisions_run_id_created_at", "run_id", "created_at"),
        Index("ix_reviewer_decisions_task_id_created_at", "task_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(uuid_type, primary_key=True, default=uuid4)
    escalation_id: Mapped[UUID] = mapped_column(
        uuid_type,
        ForeignKey("escalations.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_id: Mapped[UUID] = mapped_column(
        uuid_type,
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id: Mapped[UUID] = mapped_column(
        uuid_type,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reviewer_display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reviewer_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    escalation: Mapped["Escalation"] = relationship(back_populates="reviewer_decisions")
    run: Mapped["Run"] = relationship(back_populates="reviewer_decisions")
    task: Mapped["Task"] = relationship(back_populates="reviewer_decisions")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint(
            "verification_method IN ('deterministic', 'llm_judge', 'hybrid')",
            name="ck_ledger_entries_verification_method",
        ),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_ledger_entries_confidence",
        ),
        Index("ix_ledger_entries_run_id_created_at", "run_id", "created_at"),
        Index("ix_ledger_entries_task_id_created_at", "task_id", "created_at"),
        Index("ix_ledger_entries_attempt_id", "attempt_id"),
    )

    id: Mapped[UUID] = mapped_column(uuid_type, primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(
        uuid_type,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_id: Mapped[UUID] = mapped_column(
        uuid_type,
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_id: Mapped[UUID | None] = mapped_column(
        uuid_type,
        ForeignKey("task_attempts.id", ondelete="SET NULL"),
        nullable=True,
    )
    verification_method: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    judge_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    task: Mapped["Task"] = relationship(back_populates="ledger_entries")
    run: Mapped["Run"] = relationship(back_populates="ledger_entries")
    attempt: Mapped["TaskAttempt | None"] = relationship(back_populates="ledger_entries")
