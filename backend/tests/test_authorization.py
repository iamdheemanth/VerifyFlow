from __future__ import annotations

import asyncio
import os
from pathlib import Path
from tempfile import mkstemp
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("LLM_BASE_URL", "https://openrouter.ai/api/v1")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_MODEL", "executor-model")
os.environ.setdefault("LLM_JUDGE_MODEL", "judge-model")
os.environ.setdefault("MAX_RETRIES", "3")
os.environ.setdefault("VERIFICATION_CONFIDENCE_THRESHOLD", "0.75")

from app.core.auth import verify_token
from app.db.session import Base, get_db
from app.main import app
from app.models.domain import Escalation, LedgerEntry, Run, Task


def _sqlite_url() -> tuple[str, Path]:
    fd, raw_path = mkstemp(suffix=".db")
    os.close(fd)
    path = Path(raw_path)
    return f"sqlite+aiosqlite:///{path.as_posix()}", path


async def _seed_run_bundle(
    session: AsyncSession,
    *,
    owner_subject: str,
    owner_email: str,
    status: str = "failed",
) -> dict[str, UUID]:
    run = Run(
        id=uuid4(),
        owner_subject=owner_subject,
        owner_email=owner_email,
        goal=f"{owner_subject} run",
        acceptance_criteria="Object-level authorization is enforced",
        status=status,
    )
    task = Task(
        id=uuid4(),
        run_id=run.id,
        index=0,
        description="Authorization task",
        success_criteria="Only the owner can access this task",
        tool_name="filesystem.read_file",
        tool_params={"path": "/tmp/verifyflow/authz.txt"},
        status="escalated",
        retry_count=1,
    )
    escalation = Escalation(
        id=uuid4(),
        run_id=run.id,
        task_id=task.id,
        status="pending_review",
        failure_reason="Authorization test escalation",
        evidence_bundle={"owner": owner_subject},
    )
    ledger_entry = LedgerEntry(
        id=uuid4(),
        run_id=run.id,
        task_id=task.id,
        verification_method="deterministic",
        confidence=0.25,
        verified=False,
        evidence="Authorization test ledger entry",
        judge_reasoning=None,
    )
    session.add_all([run, task, escalation, ledger_entry])
    await session.commit()
    return {
        "run_id": run.id,
        "task_id": task.id,
        "escalation_id": escalation.id,
    }


@pytest.fixture
def authz_client():
    database_url, path = _sqlite_url()
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    auth_state = {
        "payload": {
            "sub": "user-a",
            "email": "user-a@example.com",
            "name": "User A",
        }
    }

    async def override_get_db():
        async with session_factory() as session:
            yield session

    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    def set_user(subject: str, email: str | None = None):
        auth_state["payload"] = {
            "sub": subject,
            "email": email or f"{subject}@example.com",
            "name": subject,
        }

    asyncio.run(setup())
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[verify_token] = lambda: auth_state["payload"]

    with TestClient(app) as test_client:
        yield test_client, session_factory, set_user

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())
    path.unlink(missing_ok=True)


def test_user_can_access_own_run(authz_client):
    test_client, session_factory, _set_user = authz_client

    async def seed():
        async with session_factory() as session:
            return await _seed_run_bundle(
                session,
                owner_subject="user-a",
                owner_email="user-a@example.com",
            )

    ids = asyncio.run(seed())

    response = test_client.get(f"/api/runs/{ids['run_id']}")

    assert response.status_code == 200
    assert response.json()["id"] == str(ids["run_id"])


def test_user_cannot_access_another_users_run(authz_client):
    test_client, session_factory, _set_user = authz_client

    async def seed():
        async with session_factory() as session:
            return await _seed_run_bundle(
                session,
                owner_subject="user-b",
                owner_email="user-b@example.com",
            )

    ids = asyncio.run(seed())

    response = test_client.get(f"/api/runs/{ids['run_id']}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "run_not_found"


def test_delete_run_enforces_owner(authz_client):
    test_client, session_factory, _set_user = authz_client

    async def seed():
        async with session_factory() as session:
            return await _seed_run_bundle(
                session,
                owner_subject="user-b",
                owner_email="user-b@example.com",
            )

    ids = asyncio.run(seed())

    response = test_client.delete(f"/api/runs/{ids['run_id']}")

    assert response.status_code == 404

    async def exists():
        async with session_factory() as session:
            return (await session.execute(select(Run.id).where(Run.id == ids["run_id"]))).scalar_one_or_none()

    assert asyncio.run(exists()) == ids["run_id"]


def test_ledger_enforces_run_owner(authz_client):
    test_client, session_factory, _set_user = authz_client

    async def seed():
        async with session_factory() as session:
            return await _seed_run_bundle(
                session,
                owner_subject="user-b",
                owner_email="user-b@example.com",
            )

    ids = asyncio.run(seed())

    response = test_client.get(f"/api/ledger/{ids['run_id']}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "run_not_found"


def test_review_decision_enforces_run_owner(authz_client):
    test_client, session_factory, _set_user = authz_client

    async def seed():
        async with session_factory() as session:
            own = await _seed_run_bundle(
                session,
                owner_subject="user-a",
                owner_email="user-a@example.com",
            )
            other = await _seed_run_bundle(
                session,
                owner_subject="user-b",
                owner_email="user-b@example.com",
            )
            return own, other

    own_ids, other_ids = asyncio.run(seed())

    queue_response = test_client.get("/api/review/queue")
    assert queue_response.status_code == 200
    queue_payload = queue_response.json()
    assert [item["id"] for item in queue_payload] == [str(own_ids["escalation_id"])]

    decision_response = test_client.post(
        f"/api/review/escalations/{other_ids['escalation_id']}/decision",
        json={
            "decision": "approve",
            "reviewer_key": "reviewer-a",
            "reviewer_display_name": "Reviewer A",
        },
    )

    assert decision_response.status_code == 404
    assert decision_response.json()["error"]["code"] == "escalation_not_found"


def test_stream_endpoint_enforces_run_owner(authz_client):
    test_client, session_factory, _set_user = authz_client

    async def seed():
        async with session_factory() as session:
            return await _seed_run_bundle(
                session,
                owner_subject="user-b",
                owner_email="user-b@example.com",
                status="completed",
            )

    ids = asyncio.run(seed())

    response = test_client.get(f"/api/runs/{ids['run_id']}/stream")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "run_not_found"
