from __future__ import annotations

import os
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
from app.models.domain import LedgerEntry, Run, RunTelemetry, Task, TaskAttempt
from app.services import reliability


async def _make_session() -> tuple[AsyncSession, any]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session = session_factory()
    return session, engine


@pytest.mark.asyncio
async def test_refresh_run_telemetry_aggregates_attempt_metrics_and_updates_latest_confidence():
    session, engine = await _make_session()
    try:
        run_id = uuid4()
        task_id = uuid4()
        session.add(
            Run(
                id=run_id,
                goal="Aggregate telemetry",
                acceptance_criteria="Telemetry totals should match the attempts",
                status="completed",
            )
        )
        session.add(
            Task(
                id=task_id,
                run_id=run_id,
                index=0,
                description="Collect telemetry",
                success_criteria="Telemetry is rolled up",
                tool_name="filesystem.read_file",
                tool_params={"path": "C:/tmp/demo.txt"},
                status="verified",
            )
        )
        session.add_all(
            [
                TaskAttempt(
                    run_id=run_id,
                    task_id=task_id,
                    attempt_index=0,
                    tool_name="filesystem.read_file",
                    tool_params={"path": "C:/tmp/demo.txt"},
                    execution_steps=[],
                    tool_calls=[{"tool_name": "filesystem.read_file"}],
                    verification_method="deterministic",
                    final_confidence=0.6,
                    executor_latency_ms=20,
                    verifier_latency_ms=5,
                    total_latency_ms=25,
                    token_input=11,
                    token_output=4,
                    token_total=15,
                    estimated_cost_usd=0.01,
                    outcome="retrying",
                ),
                TaskAttempt(
                    run_id=run_id,
                    task_id=task_id,
                    attempt_index=1,
                    tool_name="filesystem.read_file",
                    tool_params={"path": "C:/tmp/demo.txt"},
                    execution_steps=[],
                    tool_calls=[{"tool_name": "filesystem.read_file"}],
                    verification_method="hybrid",
                    final_confidence=1.0,
                    executor_latency_ms=30,
                    verifier_latency_ms=10,
                    total_latency_ms=40,
                    token_input=20,
                    token_output=10,
                    token_total=30,
                    estimated_cost_usd=0.05,
                    outcome="verified",
                ),
            ]
        )
        await session.commit()

        telemetry = await reliability.refresh_run_telemetry(session, str(run_id))
        await session.refresh(telemetry)
        run = (await session.execute(select(Run).where(Run.id == run_id))).scalar_one()

        assert telemetry.total_executor_latency_ms == pytest.approx(50)
        assert telemetry.total_verifier_latency_ms == pytest.approx(15)
        assert telemetry.total_task_latency_ms == pytest.approx(65)
        assert telemetry.total_retry_count == 1
        assert telemetry.total_token_input == 31
        assert telemetry.total_token_output == 14
        assert telemetry.total_token_total == 45
        assert telemetry.total_estimated_cost_usd == pytest.approx(0.06)
        assert telemetry.total_tool_calls == 2
        assert telemetry.deterministic_verifications == 1
        assert telemetry.hybrid_verifications == 1
        assert telemetry.llm_judge_verifications == 0
        assert telemetry.average_confidence == pytest.approx(0.8)
        assert run.latest_confidence == pytest.approx(1.0)
    finally:
        await session.close()
        await engine.dispose()


def test_classify_retryability_prefers_structured_error_details_over_text_guessing():
    result = reliability.classify_retryability(
        action_claim={
            "error": "429 Too Many Requests",
            "error_details": {
                "message": "Malformed JSON from provider",
                "category": "malformed_response",
                "retryable": False,
            },
        },
        verification_result=None,
    )

    assert result["retryable"] is False
    assert result["category"] == "malformed_response"
    assert result["reason"] == "Malformed JSON from provider"


@pytest.mark.asyncio
async def test_create_ledger_entry_dedupes_identical_results_but_keeps_distinct_attempts():
    session, engine = await _make_session()
    try:
        run_id = uuid4()
        task_id = uuid4()
        attempt_a = uuid4()
        attempt_b = uuid4()
        session.add(
            Run(
                id=run_id,
                goal="Ledger dedupe",
                acceptance_criteria="Identical results should dedupe per attempt only",
                status="pending",
            )
        )
        session.add(
            Task(
                id=task_id,
                run_id=run_id,
                index=0,
                description="Verify once",
                success_criteria="Ledger entries are controlled",
                tool_name="filesystem.read_file",
                tool_params={"path": "C:/tmp/demo.txt"},
                status="pending",
            )
        )
        await session.commit()

        payload = {
            "verified": False,
            "confidence": 0.7,
            "method": "deterministic",
            "evidence": "Expected text was missing.",
            "judge_reasoning": None,
        }

        created_first = await reliability.create_ledger_entry(
            session,
            run_id=str(run_id),
            task_id=str(task_id),
            result=payload,
            attempt_id=str(attempt_a),
        )
        created_duplicate = await reliability.create_ledger_entry(
            session,
            run_id=str(run_id),
            task_id=str(task_id),
            result=payload,
            attempt_id=str(attempt_a),
        )
        created_distinct_attempt = await reliability.create_ledger_entry(
            session,
            run_id=str(run_id),
            task_id=str(task_id),
            result=payload,
            attempt_id=str(attempt_b),
        )

        entries = (await session.execute(select(LedgerEntry).where(LedgerEntry.task_id == task_id))).scalars().all()
        assert created_first is True
        assert created_duplicate is False
        assert created_distinct_attempt is True
        assert len(entries) == 2
    finally:
        await session.close()
        await engine.dispose()
