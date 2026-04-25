from __future__ import annotations

import asyncio
import contextlib
import os
from datetime import timedelta
from pathlib import Path
from tempfile import mkstemp
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("LLM_BASE_URL", "https://openrouter.ai/api/v1")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_MODEL", "executor-model")
os.environ.setdefault("LLM_JUDGE_MODEL", "judge-model")
os.environ.setdefault("GITHUB_TOKEN", "test-token")
os.environ.setdefault("GITHUB_OWNER", "test-owner")
os.environ.setdefault("MAX_RETRIES", "3")
os.environ.setdefault("VERIFICATION_CONFIDENCE_THRESHOLD", "0.75")

from app.db.session import Base
from app.models.domain import Run, utcnow
from app.services import run_queue
from app.worker import run_worker

_ENGINE_PATHS: dict[int, Path] = {}


async def _make_session_factory():
    fd, raw_path = mkstemp(suffix=".db")
    os.close(fd)
    path = Path(raw_path)
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{path.as_posix()}",
        future=True,
    )
    _ENGINE_PATHS[id(engine)] = path
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return factory, engine


async def _dispose_engine(engine) -> None:
    path = _ENGINE_PATHS.pop(id(engine), None)
    await engine.dispose()
    if isinstance(path, Path):
        with contextlib.suppress(PermissionError):
            path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_worker_claims_queued_run():
    session_factory, engine = await _make_session_factory()
    run_id = uuid4()
    try:
        async with session_factory() as session:
            session.add(
                Run(
                    id=run_id,
                    goal="Queued run",
                    acceptance_criteria="Worker claims this run",
                    status="queued",
                    queued_at=utcnow(),
                )
            )
            await session.commit()

            claimed = await run_queue.claim_next_queued_run(
                session,
                worker_id="worker-a",
                lease_seconds=60,
            )

            assert claimed is not None
            assert claimed.id == run_id
            assert claimed.status == "planning"
            assert claimed.lease_owner == "worker-a"
            assert claimed.lease_expires_at is not None
            assert claimed.execution_attempts == 1

            duplicate_claim = await run_queue.claim_next_queued_run(
                session,
                worker_id="worker-b",
                lease_seconds=60,
            )
            assert duplicate_claim is None
    finally:
        await _dispose_engine(engine)


@pytest.mark.asyncio
async def test_active_worker_renews_lease_during_long_running_execution(monkeypatch: pytest.MonkeyPatch):
    session_factory, engine = await _make_session_factory()
    run_id = uuid4()
    renew_calls = 0
    original_renew = run_queue.renew_claimed_run
    monkeypatch.setattr(run_worker, "AsyncSessionLocal", session_factory)

    async def slow_graph(_run_id: str, _db: AsyncSession) -> None:
        await asyncio.sleep(0.05)

    async def counting_renew(*args, **kwargs):
        nonlocal renew_calls
        renew_calls += 1
        return await original_renew(*args, **kwargs)

    monkeypatch.setattr(run_worker, "run_graph", slow_graph)
    monkeypatch.setattr(run_queue, "renew_claimed_run", counting_renew)

    try:
        async with session_factory() as session:
            session.add(
                Run(
                    id=run_id,
                    goal="Long queued run",
                    acceptance_criteria="Worker renews this run while executing",
                    status="queued",
                    queued_at=utcnow(),
                )
            )
            await session.commit()

        processed = await run_worker.process_next_run(
            worker_id="worker-a",
            lease_seconds=60,
            heartbeat_interval_seconds=0.01,
        )
        assert processed is True
        assert renew_calls >= 1

        async with session_factory() as session:
            run = (await session.execute(select(Run).where(Run.id == run_id))).scalar_one()
            assert run.lease_owner is None
            assert run.lease_expires_at is None
            assert run.finished_at is not None
    finally:
        await _dispose_engine(engine)


@pytest.mark.asyncio
async def test_completion_succeeds_when_lease_owner_matches():
    session_factory, engine = await _make_session_factory()
    run_id = uuid4()
    try:
        async with session_factory() as session:
            session.add(
                Run(
                    id=run_id,
                    goal="Complete owned run",
                    acceptance_criteria="Completion clears the matching lease",
                    status="completed",
                    queued_at=utcnow(),
                    started_at=utcnow(),
                    lease_owner="worker-a",
                    lease_expires_at=utcnow() + timedelta(minutes=5),
                )
            )
            await session.commit()

            completed = await run_queue.complete_claimed_run(
                session,
                run_id=run_id,
                worker_id="worker-a",
            )

            assert completed is True
            run = (await session.execute(select(Run).where(Run.id == run_id))).scalar_one()
            assert run.lease_owner is None
            assert run.lease_expires_at is None
            assert run.finished_at is not None
    finally:
        await _dispose_engine(engine)


@pytest.mark.asyncio
async def test_stale_worker_cannot_complete_after_ownership_changed():
    session_factory, engine = await _make_session_factory()
    run_id = uuid4()
    lease_expires_at = utcnow() + timedelta(minutes=5)
    try:
        async with session_factory() as session:
            session.add(
                Run(
                    id=run_id,
                    goal="Recovered run",
                    acceptance_criteria="Stale completion cannot clear another worker's lease",
                    status="planning",
                    queued_at=utcnow(),
                    started_at=utcnow(),
                    lease_owner="worker-b",
                    lease_expires_at=lease_expires_at,
                )
            )
            await session.commit()

            completed = await run_queue.complete_claimed_run(
                session,
                run_id=run_id,
                worker_id="worker-a",
            )

            assert completed is False
            run = (await session.execute(select(Run).where(Run.id == run_id))).scalar_one()
            assert run.lease_owner == "worker-b"
            assert run.lease_expires_at == lease_expires_at.replace(tzinfo=None)
            assert run.finished_at is None
    finally:
        await _dispose_engine(engine)


@pytest.mark.asyncio
async def test_worker_failed_run_records_error(monkeypatch: pytest.MonkeyPatch):
    session_factory, engine = await _make_session_factory()
    run_id = uuid4()
    monkeypatch.setattr(run_worker, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(
        run_worker,
        "run_graph",
        AsyncMock(side_effect=RuntimeError("Worker graph crashed")),
    )

    try:
        async with session_factory() as session:
            session.add(
                Run(
                    id=run_id,
                    goal="Crash queued run",
                    acceptance_criteria="Failure should be recorded",
                    status="queued",
                    queued_at=utcnow(),
                )
            )
            await session.commit()

        processed = await run_worker.process_next_run(worker_id="worker-a")
        assert processed is True

        async with session_factory() as session:
            run = (await session.execute(select(Run).where(Run.id == run_id))).scalar_one()
            assert run.status == "failed"
            assert run.last_worker_error == "Worker graph crashed"
            assert run.failure_record["category"] == "run_worker_failure"
            assert run.failure_record["exception_type"] == "RuntimeError"
            assert run.lease_owner is None
            assert run.lease_expires_at is None
            assert run.finished_at is not None
    finally:
        await _dispose_engine(engine)


@pytest.mark.asyncio
async def test_failure_succeeds_when_lease_owner_matches():
    session_factory, engine = await _make_session_factory()
    run_id = uuid4()
    try:
        async with session_factory() as session:
            session.add(
                Run(
                    id=run_id,
                    goal="Owned failed run",
                    acceptance_criteria="Failure clears the matching lease",
                    status="executing",
                    queued_at=utcnow(),
                    started_at=utcnow(),
                    lease_owner="worker-a",
                    lease_expires_at=utcnow() + timedelta(minutes=5),
                )
            )
            await session.commit()

            recorded = await run_queue.record_worker_failure(
                session,
                run_id=run_id,
                worker_id="worker-a",
                exc=RuntimeError("Owned worker failure"),
            )

            assert recorded is True
            run = (await session.execute(select(Run).where(Run.id == run_id))).scalar_one()
            assert run.status == "failed"
            assert run.failure_record["category"] == "run_worker_failure"
            assert run.last_worker_error == "Owned worker failure"
            assert run.lease_owner is None
            assert run.lease_expires_at is None
            assert run.finished_at is not None
    finally:
        await _dispose_engine(engine)


@pytest.mark.asyncio
async def test_stale_worker_cannot_fail_after_ownership_changed():
    session_factory, engine = await _make_session_factory()
    run_id = uuid4()
    existing_failure_record = {"category": "stuck_run", "message": "Recovered elsewhere"}
    try:
        async with session_factory() as session:
            session.add(
                Run(
                    id=run_id,
                    goal="Recovered failed run",
                    acceptance_criteria="Stale failure cannot overwrite another worker's run",
                    status="planning",
                    failure_record=existing_failure_record,
                    queued_at=utcnow(),
                    started_at=utcnow(),
                    lease_owner="worker-b",
                    lease_expires_at=utcnow() + timedelta(minutes=5),
                )
            )
            await session.commit()

            recorded = await run_queue.record_worker_failure(
                session,
                run_id=run_id,
                worker_id="worker-a",
                exc=RuntimeError("Stale worker failure"),
            )

            assert recorded is False
            run = (await session.execute(select(Run).where(Run.id == run_id))).scalar_one()
            assert run.status == "planning"
            assert run.failure_record == existing_failure_record
            assert run.last_worker_error is None
            assert run.lease_owner == "worker-b"
            assert run.finished_at is None
    finally:
        await _dispose_engine(engine)


@pytest.mark.asyncio
async def test_lease_renewal_fails_when_lease_owner_does_not_match():
    session_factory, engine = await _make_session_factory()
    run_id = uuid4()
    lease_expires_at = utcnow() + timedelta(minutes=5)
    try:
        async with session_factory() as session:
            session.add(
                Run(
                    id=run_id,
                    goal="Lease conflict run",
                    acceptance_criteria="Stale worker cannot renew another worker's lease",
                    status="executing",
                    queued_at=utcnow(),
                    started_at=utcnow(),
                    lease_owner="worker-b",
                    lease_expires_at=lease_expires_at,
                )
            )
            await session.commit()

            renewed = await run_queue.renew_claimed_run(
                session,
                run_id=run_id,
                worker_id="worker-a",
                lease_seconds=60,
            )

            assert renewed is False
            run = (await session.execute(select(Run).where(Run.id == run_id))).scalar_one()
            assert run.lease_owner == "worker-b"
            assert run.lease_expires_at == lease_expires_at.replace(tzinfo=None)
    finally:
        await _dispose_engine(engine)


@pytest.mark.asyncio
async def test_stuck_run_detection_marks_expired_active_run_failed():
    session_factory, engine = await _make_session_factory()
    run_id = uuid4()
    try:
        async with session_factory() as session:
            session.add(
                Run(
                    id=run_id,
                    goal="Stuck run",
                    acceptance_criteria="Maintenance records stuck state",
                    status="executing",
                    queued_at=utcnow() - timedelta(hours=2),
                    started_at=utcnow() - timedelta(hours=2),
                    lease_owner="worker-a",
                    lease_expires_at=utcnow() - timedelta(minutes=5),
                )
            )
            await session.commit()

            stuck_runs = await run_queue.detect_stuck_runs(
                session,
                stale_after=timedelta(minutes=1),
            )
            assert [run.id for run in stuck_runs] == [run_id]

            failed = await run_queue.mark_stuck_runs_failed(
                session,
                stale_after=timedelta(minutes=1),
                worker_id="maintenance",
            )

            assert [run.id for run in failed] == [run_id]
            assert failed[0].status == "failed"
            assert failed[0].failure_record["category"] == "stuck_run"
            assert failed[0].failure_record["previous_status"] == "executing"
            assert failed[0].last_worker_error
            assert failed[0].lease_owner is None
            assert failed[0].lease_expires_at is None
    finally:
        await _dispose_engine(engine)
