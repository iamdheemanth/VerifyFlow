from __future__ import annotations

import asyncio
import os
from pathlib import Path
from tempfile import mkstemp

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("LLM_BASE_URL", "https://openrouter.ai/api/v1")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_MODEL", "executor-model")
os.environ.setdefault("LLM_JUDGE_MODEL", "judge-model")
os.environ.setdefault("NEXTAUTH_SECRET", "test-nextauth-secret-value-32-chars")
os.environ.setdefault("GITHUB_TOKEN", "test-token")
os.environ.setdefault("GITHUB_OWNER", "test-owner")
os.environ.setdefault("MAX_RETRIES", "3")
os.environ.setdefault("VERIFICATION_CONFIDENCE_THRESHOLD", "0.75")

from app.core.auth import verify_token
from app.db.session import Base, get_db
from app.main import app


def _sqlite_url() -> tuple[str, Path]:
    fd, raw_path = mkstemp(suffix=".db")
    os.close(fd)
    path = Path(raw_path)
    return f"sqlite+aiosqlite:///{path.as_posix()}", path


@pytest.fixture
def benchmark_client():
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

    def set_user(subject: str):
        auth_state["payload"] = {
            "sub": subject,
            "email": f"{subject}@example.com",
            "name": subject,
        }

    asyncio.run(setup())
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[verify_token] = lambda: auth_state["payload"]

    with TestClient(app) as test_client:
        yield test_client, set_user

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())
    path.unlink(missing_ok=True)


def _create_case(test_client: TestClient) -> dict:
    response = test_client.post(
        "/api/benchmarks/cases",
        json={
            "suite_name": "Local Smoke Suite",
            "name": "Create README",
            "goal": "Create README.md with benchmark content",
            "acceptance_criteria": "README.md contains benchmark content",
            "expected_outcome": "completed",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_benchmark_suite_and_case(benchmark_client):
    test_client, _set_user = benchmark_client

    suite_response = test_client.post(
        "/api/benchmarks/suites",
        json={"name": "Local Smoke Suite", "description": "Local workflow checks"},
    )
    assert suite_response.status_code == 201
    suite = suite_response.json()

    case_response = test_client.post(
        "/api/benchmarks/cases",
        json={
            "suite_id": suite["id"],
            "name": "Create README",
            "goal": "Create README.md with benchmark content",
            "acceptance_criteria": "README.md contains benchmark content",
        },
    )

    assert case_response.status_code == 201
    case = case_response.json()
    assert case["suite_id"] == suite["id"]
    assert case["name"] == "Create README"

    cases = test_client.get("/api/benchmarks/cases").json()
    suites = test_client.get("/api/benchmarks/suites").json()
    assert [item["id"] for item in cases] == [case["id"]]
    assert [item["id"] for item in suites] == [suite["id"]]


def test_run_benchmark_case_creates_benchmark_run_and_overview(benchmark_client):
    test_client, _set_user = benchmark_client
    case = _create_case(test_client)

    run_response = test_client.post(f"/api/benchmarks/cases/{case['id']}/runs")

    assert run_response.status_code == 201
    run_payload = run_response.json()
    assert run_payload["kind"] == "benchmark"
    assert run_payload["status"] == "queued"

    run = test_client.get(f"/api/runs/{run_payload['run_id']}").json()
    assert run["kind"] == "benchmark"
    assert run["benchmark_case"]["id"] == case["id"]

    overview = test_client.get("/api/benchmarks/overview").json()
    assert len(overview) == 1
    assert overview[0]["suite_name"] == "Local Smoke Suite"
    assert overview[0]["run_count"] == 1


def test_create_run_with_benchmark_case_id_marks_run_as_benchmark(benchmark_client):
    test_client, _set_user = benchmark_client
    case = _create_case(test_client)

    response = test_client.post(
        "/api/runs",
        json={
            "goal": case["goal"],
            "acceptance_criteria": case["acceptance_criteria"],
            "benchmark_case_id": case["id"],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["kind"] == "benchmark"
    assert payload["status"] == "queued"


def test_user_cannot_access_or_run_another_users_benchmark_case(benchmark_client):
    test_client, set_user = benchmark_client
    case = _create_case(test_client)

    set_user("user-b")

    assert test_client.get("/api/benchmarks/cases").json() == []
    assert test_client.post(f"/api/benchmarks/cases/{case['id']}/runs").status_code == 404
    response = test_client.post(
        "/api/runs",
        json={
            "goal": case["goal"],
            "acceptance_criteria": case["acceptance_criteria"],
            "benchmark_case_id": case["id"],
        },
    )
    assert response.status_code == 404
