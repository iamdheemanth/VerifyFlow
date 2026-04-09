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
