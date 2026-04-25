from __future__ import annotations

import asyncio
import os
from pathlib import Path
from tempfile import mkstemp
from uuid import UUID, uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agents import executor as executor_module
from app.agents import planner
from app.core.auth import verify_token
from app.core.config import Settings, settings
from app.core.filesystem_sandbox import FilesystemSandboxError
from app.db.session import Base, get_db
from app.main import app
from app.models.domain import Escalation, Run, Task


REQUIRED_ENV = {
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "LLM_BASE_URL": "https://openrouter.ai/api/v1",
    "LLM_API_KEY": "test-key",
    "LLM_MODEL": "executor-model",
    "LLM_JUDGE_MODEL": "judge-model",
    "NEXTAUTH_SECRET": "test-nextauth-secret-value-32-chars",
    "MAX_RETRIES": "3",
    "VERIFICATION_CONFIDENCE_THRESHOLD": "0.75",
}


def _sqlite_url() -> tuple[str, Path]:
    fd, raw_path = mkstemp(suffix=".db")
    os.close(fd)
    return f"sqlite+aiosqlite:///{Path(raw_path).as_posix()}", Path(raw_path)


@pytest.fixture
def allowed_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "allowed"
    root.mkdir()
    monkeypatch.setattr(settings, "filesystem_allowed_paths", [str(root)])
    return root


@pytest.fixture
def security_client():
    database_url, path = _sqlite_url()
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    auth_payload = {
        "sub": "user-a",
        "email": "user-a@example.com",
        "name": "User A",
    }

    async def override_get_db():
        async with session_factory() as session:
            yield session

    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(setup())
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[verify_token] = lambda: auth_payload

    with TestClient(app) as test_client:
        yield test_client, session_factory

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(verify_token, None)
    asyncio.run(engine.dispose())
    path.unlink(missing_ok=True)


async def _seed_run(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_subject: str,
    status: str = "completed",
) -> UUID:
    async with session_factory() as session:
        run = Run(
            id=uuid4(),
            owner_subject=owner_subject,
            owner_email=f"{owner_subject}@example.com",
            goal=f"{owner_subject} security regression run",
            acceptance_criteria="Access remains scoped to the owner.",
            status=status,
        )
        session.add(run)
        await session.commit()
        return run.id


@pytest.mark.asyncio
async def test_filesystem_sandbox_allows_writes_inside_allowed_path(allowed_root: Path):
    target = allowed_root / "nested" / "proof.txt"

    result = await executor_module._call_filesystem(
        "filesystem.write_file",
        {"path": str(target), "content": "ok"},
    )

    assert result["is_error"] is False
    assert target.read_text(encoding="utf-8") == "ok"


@pytest.mark.asyncio
async def test_filesystem_sandbox_rejects_path_traversal(tmp_path: Path, allowed_root: Path):
    target = allowed_root / ".." / "escaped.txt"

    with pytest.raises(FilesystemSandboxError):
        await executor_module._call_filesystem(
            "filesystem.write_file",
            {"path": str(target), "content": "blocked"},
        )

    assert not (tmp_path / "escaped.txt").exists()


@pytest.mark.asyncio
async def test_filesystem_sandbox_rejects_absolute_path_outside_allowed_base(tmp_path: Path, allowed_root: Path):
    target = tmp_path / "outside.txt"

    with pytest.raises(FilesystemSandboxError):
        await executor_module._call_filesystem(
            "filesystem.write_file",
            {"path": str(target), "content": "blocked"},
        )

    assert not target.exists()


@pytest.mark.asyncio
async def test_filesystem_sandbox_rejects_symlink_escape_if_supported(tmp_path: Path, allowed_root: Path):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = allowed_root / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"Symlink creation is not supported in this environment: {exc}")

    escaped_target = outside / "escape.txt"

    with pytest.raises(FilesystemSandboxError):
        await executor_module._call_filesystem(
            "filesystem.write_file",
            {"path": str(link / "escape.txt"), "content": "blocked"},
        )

    assert not escaped_target.exists()


def test_api_rejects_missing_bearer_token():
    original_override = app.dependency_overrides.pop(verify_token, None)
    try:
        response = TestClient(app).get("/health")
    finally:
        if original_override is not None:
            app.dependency_overrides[verify_token] = original_override

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_api_rejects_invalid_bearer_token():
    original_override = app.dependency_overrides.pop(verify_token, None)
    try:
        response = TestClient(app).get("/health", headers={"Authorization": "Bearer not-a-valid-jwt"})
    finally:
        if original_override is not None:
            app.dependency_overrides[verify_token] = original_override

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_missing_nextauth_secret_fails_config_validation(monkeypatch: pytest.MonkeyPatch):
    for name, value in REQUIRED_ENV.items():
        if name == "NEXTAUTH_SECRET":
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert "NEXTAUTH_SECRET" in str(exc_info.value)
    assert "Field required" in str(exc_info.value)


def test_user_cannot_access_another_users_run(security_client):
    test_client, session_factory = security_client
    run_id = asyncio.run(_seed_run(session_factory, owner_subject="user-b"))

    response = test_client.get(f"/api/runs/{run_id}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "run_not_found"


def test_user_cannot_delete_another_users_run(security_client):
    test_client, session_factory = security_client
    run_id = asyncio.run(_seed_run(session_factory, owner_subject="user-b"))

    response = test_client.delete(f"/api/runs/{run_id}")

    assert response.status_code == 404

    async def run_still_exists() -> bool:
        async with session_factory() as session:
            return (await session.execute(select(Run.id).where(Run.id == run_id))).scalar_one_or_none() == run_id

    assert asyncio.run(run_still_exists()) is True


@pytest.mark.asyncio
async def test_planner_fallback_escalates_without_fake_filesystem_success_task(monkeypatch: pytest.MonkeyPatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    monkeypatch.setattr(
        "app.core.llm.executor_llm.chat_json",
        AsyncMock(
            return_value={
                "tasks": [
                    {
                        "description": "Book the unsupported trip",
                        "success_criteria": "A confirmed itinerary exists",
                        "tool_name": "travel.book_flight",
                        "tool_params": {"destination": "Mars"},
                    }
                ]
            }
        ),
    )

    run_id = uuid4()
    state = {
        "run_id": str(run_id),
        "goal": "Book a flight to Mars.",
        "acceptance_criteria": "A confirmed itinerary is available.",
        "tasks": [],
        "current_task_index": -1,
        "current_task": None,
        "action_claim": None,
        "verification_result": None,
        "retry_count": 0,
        "error": None,
    }

    async with session_factory() as session:
        session.add(
            Run(
                id=run_id,
                goal=state["goal"],
                acceptance_criteria=state["acceptance_criteria"],
                status="pending",
            )
        )
        await session.commit()

        planned_state = await planner.plan(state, session)
        run = (await session.execute(select(Run).where(Run.id == run_id))).scalar_one()
        tasks = (await session.execute(select(Task).where(Task.run_id == run_id))).scalars().all()
        escalations = (await session.execute(select(Escalation).where(Escalation.run_id == run_id))).scalars().all()

    assert planned_state["decision"] == "finish"
    assert run.status == "needs_review"
    assert run.failure_record["category"] == "planning_failed"
    assert run.failure_record["original_goal"] == state["goal"]
    assert [task.tool_name for task in tasks] == ["planner.manual_review"]
    assert tasks[0].status == "escalated"
    assert tasks[0].claimed_result["claimed_success"] is False
    assert "planning_failure" in tasks[0].tool_params
    assert len(escalations) == 1
    assert escalations[0].status == "pending_review"

    await engine.dispose()


def test_stream_endpoint_requires_authentication(security_client):
    test_client, session_factory = security_client
    run_id = asyncio.run(_seed_run(session_factory, owner_subject="user-a"))
    original_override = app.dependency_overrides.pop(verify_token, None)

    try:
        response = test_client.get(f"/api/runs/{run_id}/stream")
    finally:
        if original_override is not None:
            app.dependency_overrides[verify_token] = original_override

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_stream_endpoint_enforces_run_ownership(security_client):
    test_client, session_factory = security_client
    run_id = asyncio.run(_seed_run(session_factory, owner_subject="user-b"))

    response = test_client.get(f"/api/runs/{run_id}/stream")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "run_not_found"
