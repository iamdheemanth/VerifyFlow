from __future__ import annotations

import asyncio
import os
from pathlib import Path
from tempfile import mkstemp
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
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

from app.db.session import Base, get_db
from app.main import app
from app.models.domain import Task
from app.orchestrator import graph as graph_module
from app.worker import run_worker


def _sqlite_url() -> tuple[str, Path]:
    fd, raw_path = mkstemp(suffix=".db")
    os.close(fd)
    path = Path(raw_path)
    return f"sqlite+aiosqlite:///{path.as_posix()}", path


@pytest.fixture
def e2e_client(monkeypatch: pytest.MonkeyPatch):
    database_url, path = _sqlite_url()
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(setup())
    app.dependency_overrides[get_db] = override_get_db

    async def planner_stub(state, db):
        run_id = UUID(state["run_id"])
        db.add(
            Task(
                run_id=run_id,
                index=0,
                description="Create a local proof file",
                success_criteria="The file is written successfully",
                tool_name="filesystem.write_file",
                tool_params={"path": "C:/tmp/verifyflow-proof.txt", "content": "ok"},
                status="pending",
            )
        )
        await db.commit()
        refreshed_run = await graph_module._load_run(db, state["run_id"])
        return {
            **state,
            "tasks": [graph_module._serialize_task(task) for task in refreshed_run.tasks],
        }

    monkeypatch.setattr(graph_module.planner, "plan", planner_stub)
    monkeypatch.setattr(
        graph_module.executor,
        "execute",
        AsyncMock(
            side_effect=lambda state, db: {
                **state,
                "action_claim": {
                    "tool_name": state["current_task"]["tool_name"],
                    "params": state["current_task"]["tool_params"],
                    "result": {"written": True},
                    "claimed_success": True,
                    "claimed_at": "now",
                },
                "error": None,
            }
        ),
    )
    monkeypatch.setattr(
        graph_module.registry,
        "verify",
        AsyncMock(
            return_value=graph_module.VerificationResult(
                verified=True,
                confidence=1.0,
                method="deterministic",
                evidence="File write verified",
            )
        ),
    )
    monkeypatch.setattr(graph_module.registry, "needs_judge", lambda result: False)
    monkeypatch.setattr(graph_module.executor, "reset_browser_clients", AsyncMock())
    monkeypatch.setattr(run_worker, "AsyncSessionLocal", session_factory)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())
    path.unlink(missing_ok=True)


def test_create_run_executes_graph_and_persists_run_task_and_telemetry(e2e_client):
    response = e2e_client.post(
        "/api/runs",
        json={
            "goal": "Create a local proof file",
            "acceptance_criteria": "The file write is verified",
        },
    )

    assert response.status_code == 201
    created_payload = response.json()
    assert created_payload["status"] == "queued"
    run_id = created_payload["id"]

    assert asyncio.run(run_worker.process_next_run(worker_id="test-worker")) is True

    run_response = e2e_client.get(f"/api/runs/{run_id}")
    assert run_response.status_code == 200
    run_payload = run_response.json()
    assert run_payload["status"] == "completed"
    assert len(run_payload["tasks"]) == 1
    assert run_payload["tasks"][0]["status"] == "verified"
    assert run_payload["telemetry"]["deterministic_verifications"] == 1
    assert run_payload["telemetry"]["total_tool_calls"] == 1
    assert run_payload["telemetry"]["average_confidence"] == 1.0

    overview_response = e2e_client.get("/api/runs/overview")
    assert overview_response.status_code == 200
    overview_payload = overview_response.json()
    assert overview_payload["total_runs"] == 1
    assert overview_payload["completed_runs"] == 1
    assert overview_payload["failed_runs"] == 0
    assert overview_payload["total_tokens"] == 0


def test_create_run_persists_catastrophic_failure_evidence_when_graph_crashes(e2e_client, monkeypatch: pytest.MonkeyPatch):
    async def planner_stub(state, db):
        run_id = UUID(state["run_id"])
        db.add(
            Task(
                run_id=run_id,
                index=0,
                description="Crash during execution",
                success_criteria="Catastrophic evidence is persisted",
                tool_name="filesystem.write_file",
                tool_params={"path": "C:/tmp/verifyflow-proof.txt", "content": "ok"},
                status="pending",
            )
        )
        await db.commit()
        refreshed_run = await graph_module._load_run(db, state["run_id"])
        return {
            **state,
            "tasks": [graph_module._serialize_task(task) for task in refreshed_run.tasks],
        }

    monkeypatch.setattr(graph_module.planner, "plan", planner_stub)
    monkeypatch.setattr(
        graph_module.executor,
        "execute",
        AsyncMock(side_effect=RuntimeError("Filesystem worker crashed hard")),
    )

    response = e2e_client.post(
        "/api/runs",
        json={
            "goal": "Crash the graph",
            "acceptance_criteria": "Failure evidence is persisted",
        },
    )

    assert response.status_code == 201
    created_payload = response.json()
    assert created_payload["status"] == "queued"
    run_id = created_payload["id"]

    assert asyncio.run(run_worker.process_next_run(worker_id="test-worker")) is True

    run_response = e2e_client.get(f"/api/runs/{run_id}")
    assert run_response.status_code == 200
    run_payload = run_response.json()
    assert run_payload["status"] == "failed"
    assert run_payload["failure_record"]["category"] == "catastrophic_orchestration_failure"
    assert "Filesystem worker crashed hard" in run_payload["failure_record"]["message"]
    assert run_payload["tasks"][0]["status"] == "escalated"

    inspection_response = e2e_client.get(f"/api/runs/{run_id}/inspection")
    assert inspection_response.status_code == 200
    inspection_payload = inspection_response.json()
    assert inspection_payload["task_inspections"][0]["attempts"][0]["verification_payload"]["outcome"] == "catastrophic_failure"
    assert inspection_payload["task_inspections"][0]["escalations"][0]["status"] == "pending_review"
