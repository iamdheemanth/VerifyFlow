from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Run, utcnow

QUEUED = "queued"
ACTIVE_STATUSES = {"planning", "executing", "verifying"}
TERMINAL_STATUSES = {"completed", "failed", "needs_review"}


def _trim_message(message: str, *, limit: int = 1000) -> str:
    stripped = message.strip() or "Unknown worker failure"
    return stripped if len(stripped) <= limit else stripped[: limit - 3] + "..."


def _worker_failure_record(
    *,
    category: str,
    message: str,
    worker_id: str | None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "category": category,
        "message": _trim_message(message),
        "worker_id": worker_id,
        "recorded_at": utcnow().isoformat(),
    }
    if extra:
        record.update(extra)
    return record


async def enqueue_run(db: AsyncSession, run_id: UUID | str) -> Run:
    run_uuid = UUID(str(run_id))
    run = await db.get(Run, run_uuid)
    if run is None:
        raise ValueError(f"Run {run_id} was not found.")

    now = utcnow()
    run.status = QUEUED
    run.queued_at = now
    run.started_at = None
    run.finished_at = None
    run.lease_owner = None
    run.lease_expires_at = None
    run.last_worker_error = None
    run.updated_at = now
    await db.commit()
    await db.refresh(run)
    return run


async def claim_next_queued_run(
    db: AsyncSession,
    *,
    worker_id: str,
    lease_seconds: int = 1800,
) -> Run | None:
    candidate_result = await db.execute(
        select(Run.id)
        .where(Run.status == QUEUED)
        .order_by(Run.queued_at.asc(), Run.created_at.asc())
        .limit(1)
    )
    run_id = candidate_result.scalar_one_or_none()
    if run_id is None:
        return None

    now = utcnow()
    lease_expires_at = now + timedelta(seconds=lease_seconds)
    result = await db.execute(
        update(Run)
        .where(Run.id == run_id, Run.status == QUEUED)
        .values(
            status="planning",
            started_at=now,
            lease_owner=worker_id,
            lease_expires_at=lease_expires_at,
            execution_attempts=Run.execution_attempts + 1,
            last_worker_error=None,
            updated_at=now,
        )
    )
    if result.rowcount != 1:
        await db.rollback()
        return None

    await db.commit()
    run = await db.get(Run, run_id)
    return run


async def renew_claimed_run(
    db: AsyncSession,
    *,
    run_id: UUID | str,
    worker_id: str,
    lease_seconds: int = 1800,
) -> bool:
    now = utcnow()
    lease_expires_at = now + timedelta(seconds=lease_seconds)
    result = await db.execute(
        update(Run)
        .where(
            Run.id == UUID(str(run_id)),
            Run.lease_owner == worker_id,
        )
        .values(
            lease_expires_at=lease_expires_at,
            updated_at=now,
        )
    )
    if result.rowcount != 1:
        await db.rollback()
        return False

    await db.commit()
    return True


async def complete_claimed_run(
    db: AsyncSession,
    *,
    run_id: UUID | str,
    worker_id: str,
) -> bool:
    now = utcnow()
    result = await db.execute(
        update(Run)
        .where(
            Run.id == UUID(str(run_id)),
            Run.lease_owner == worker_id,
        )
        .values(
            lease_owner=None,
            lease_expires_at=None,
            finished_at=now,
            updated_at=now,
        )
    )
    if result.rowcount != 1:
        await db.rollback()
        return False

    await db.commit()
    return True


async def record_worker_failure(
    db: AsyncSession,
    *,
    run_id: UUID | str,
    worker_id: str,
    exc: Exception,
) -> bool:
    run_uuid = UUID(str(run_id))
    message = _trim_message(str(exc) or exc.__class__.__name__)
    now = utcnow()
    worker_record = _worker_failure_record(
        category="run_worker_failure",
        message=message,
        worker_id=worker_id,
        extra={"exception_type": exc.__class__.__name__},
    )
    run = await db.get(Run, run_uuid)
    if run is None or run.lease_owner != worker_id:
        await db.rollback()
        return False

    if isinstance(run.failure_record, dict):
        run.failure_record = {**run.failure_record, "worker_failure": worker_record}
    else:
        run.failure_record = worker_record
    run.status = "failed"
    run.last_worker_error = message
    run.lease_owner = None
    run.lease_expires_at = None
    run.finished_at = now
    run.updated_at = now
    await db.commit()
    return True


async def detect_stuck_runs(
    db: AsyncSession,
    *,
    stale_after: timedelta,
) -> list[Run]:
    now = utcnow()
    updated_cutoff = now - stale_after
    result = await db.execute(
        select(Run)
        .where(Run.status.in_(ACTIVE_STATUSES))
        .where(
            or_(
                Run.lease_expires_at.is_not(None) & (Run.lease_expires_at <= now),
                Run.updated_at <= updated_cutoff,
            )
        )
        .order_by(Run.updated_at.asc())
    )
    return list(result.scalars().all())


async def mark_stuck_runs_failed(
    db: AsyncSession,
    *,
    stale_after: timedelta,
    worker_id: str | None = None,
) -> list[Run]:
    stuck_runs = await detect_stuck_runs(db, stale_after=stale_after)
    now = utcnow()
    for run in stuck_runs:
        previous_status = run.status
        message = f"Run was stuck in {previous_status} beyond the allowed worker lease."
        run.status = "failed"
        run.failure_record = _worker_failure_record(
            category="stuck_run",
            message=message,
            worker_id=worker_id,
            extra={
                "previous_status": previous_status,
                "lease_expires_at": run.lease_expires_at.isoformat() if run.lease_expires_at else None,
            },
        )
        run.last_worker_error = message
        run.lease_owner = None
        run.lease_expires_at = None
        run.finished_at = now
        run.updated_at = now

    await db.commit()
    for run in stuck_runs:
        await db.refresh(run)
    return stuck_runs
