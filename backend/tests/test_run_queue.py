from __future__ import annotations

import os
from datetime import timedelta
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


async def _make_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return factory, engine


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
        await engine.dispose()


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
        await engine.dispose()


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
        await engine.dispose()
