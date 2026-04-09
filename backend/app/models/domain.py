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
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


uuid_type = Uuid(as_uuid=True)
json_type = JSON().with_variant(JSONB, "postgresql")


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'planning', 'executing', 'completed', 'failed')",
            name="ck_runs_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_type, primary_key=True, default=uuid4)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    acceptance_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
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
    )
    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'executing', 'claimed', 'verified', 'failed', 'escalated')",
            name="ck_tasks_status",
        ),
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
    )


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
    )

    id: Mapped[UUID] = mapped_column(uuid_type, primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(
        uuid_type,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_id: Mapped[UUID] = mapped_column(
        uuid_type,
        ForeignKey("runs.id"),
        nullable=False,
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
