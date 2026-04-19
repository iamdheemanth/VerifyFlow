from __future__ import annotations

import os
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
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
from app.models.domain import Run, Task
from app.orchestrator import graph as graph_module
from app.orchestrator.graph import run_graph


@pytest.mark.asyncio
async def test_run_graph_verifies_all_tasks(monkeypatch: pytest.MonkeyPatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    monkeypatch.setattr(
        graph_module.registry,
        "verify",
        AsyncMock(
            return_value=graph_module.VerificationResult(
                verified=True,
                confidence=1.0,
                method="deterministic",
                evidence="Stub verification passed",
            )
        ),
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    run_id = uuid4()
    async with session_factory() as session:
        run = Run(
            id=run_id,
            goal="Verify the stub workflow",
            acceptance_criteria="Both tasks should end verified",
            status="pending",
        )
        tasks = [
            Task(
                run_id=run_id,
                index=0,
                description="First task",
                success_criteria="First task succeeds",
                tool_name="stub.first",
                tool_params={"step": 1},
                status="pending",
            ),
            Task(
                run_id=run_id,
                index=1,
                description="Second task",
                success_criteria="Second task succeeds",
                tool_name="stub.second",
                tool_params={"step": 2},
                status="pending",
            ),
        ]
        session.add(run)
        session.add_all(tasks)
        await session.commit()

        await run_graph(str(run_id), session)

        await session.refresh(tasks[0])
        await session.refresh(tasks[1])

        assert tasks[0].status == "verified"
        assert tasks[1].status == "verified"

    await engine.dispose()


@pytest.mark.asyncio
async def test_run_graph_stops_after_escalated_task(monkeypatch: pytest.MonkeyPatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    verify_mock = AsyncMock(
        return_value=graph_module.VerificationResult(
            verified=False,
            confidence=0.7,
            method="deterministic",
            evidence="Forced failure",
        )
    )
    monkeypatch.setattr(graph_module.registry, "verify", verify_mock)
    monkeypatch.setattr(graph_module.registry, "needs_judge", lambda result: False)
    monkeypatch.setattr(graph_module.executor, "reset_browser_clients", AsyncMock())
    monkeypatch.setattr(
        graph_module.executor,
        "execute",
        AsyncMock(
            side_effect=lambda state, db: {
                **state,
                "action_claim": {
                    "tool_name": state["current_task"]["tool_name"],
                    "params": state["current_task"]["tool_params"],
                    "result": {"is_error": True},
                    "claimed_success": False,
                    "claimed_at": "now",
                    "error": "forced failure",
                },
                "error": "forced failure",
            }
        ),
    )

    run_id = uuid4()
    async with session_factory() as session:
        run = Run(
            id=run_id,
            goal="Stop after first failed task",
            acceptance_criteria="Second task must remain untouched",
            status="pending",
        )
        tasks = [
            Task(
                run_id=run_id,
                index=0,
                description="First task fails",
                success_criteria="It fails",
                tool_name="browser.fill",
                tool_params={"selector": "#q", "value": "Wikipedia"},
                status="pending",
                retry_count=3,
            ),
            Task(
                run_id=run_id,
                index=1,
                description="Second task should never execute",
                success_criteria="It stays pending",
                tool_name="browser.click",
                tool_params={"selector": "button"},
                status="pending",
            ),
        ]
        session.add(run)
        session.add_all(tasks)
        await session.commit()

        await run_graph(str(run_id), session)

        await session.refresh(run)
        await session.refresh(tasks[0])
        await session.refresh(tasks[1])

        assert run.status == "failed"
        assert tasks[0].status == "escalated"
        assert tasks[1].status == "pending"

    await engine.dispose()
