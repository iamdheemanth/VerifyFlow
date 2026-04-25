from __future__ import annotations

import asyncio
import os
from pathlib import Path
from tempfile import mkstemp

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
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

from app.db.session import Base, get_db
from app.main import app
from app.models.domain import BenchmarkCase, BenchmarkSuite, Run
from app.routes.demo import DEMO_SUITE_NAME


def _sqlite_url() -> tuple[str, Path]:
    fd, raw_path = mkstemp(suffix=".db")
    os.close(fd)
    path = Path(raw_path)
    return f"sqlite+aiosqlite:///{path.as_posix()}", path


@pytest.fixture
def client():
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

    with TestClient(app) as test_client:
        yield test_client, session_factory

    app.dependency_overrides.pop(get_db, None)
    asyncio.run(engine.dispose())
    path.unlink(missing_ok=True)


async def _count_demo_data(session_factory) -> dict[str, int]:
    async with session_factory() as session:
        suite = (
            await session.execute(select(BenchmarkSuite).where(BenchmarkSuite.name == DEMO_SUITE_NAME))
        ).scalar_one_or_none()
        suite_count = (
            await session.execute(select(func.count(BenchmarkSuite.id)))
        ).scalar_one()
        case_count = (
            await session.execute(select(func.count(BenchmarkCase.id)))
        ).scalar_one()
        benchmark_run_count = (
            await session.execute(
                select(func.count(Run.id)).where(
                    Run.owner_subject == "test-user",
                    Run.kind == "benchmark",
                    Run.benchmark_suite_id == (suite.id if suite else None),
                )
            )
        ).scalar_one()
        standard_run_count = (
            await session.execute(
                select(func.count(Run.id)).where(
                    Run.owner_subject == "test-user",
                    Run.kind == "standard",
                )
            )
        ).scalar_one()
    return {
        "suites": suite_count,
        "cases": case_count,
        "benchmark_runs": benchmark_run_count,
        "standard_runs": standard_run_count,
    }


def test_user_with_no_data_can_seed_demo_benchmark_data(client):
    test_client, session_factory = client

    response = test_client.post("/api/demo/seed")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "created_runs": 2,
        "created_suites": 1,
        "created_cases": 2,
        "message": "Demo benchmark data created.",
    }
    counts = asyncio.run(_count_demo_data(session_factory))
    assert counts["suites"] == 1
    assert counts["cases"] == 2
    assert counts["benchmark_runs"] == 2


def test_user_with_existing_standard_runs_can_seed_demo_benchmark_data(client):
    test_client, session_factory = client

    async def seed_standard_run():
        async with session_factory() as session:
            session.add(
                Run(
                    owner_subject="test-user",
                    owner_email="test@example.com",
                    goal="Existing normal run",
                    acceptance_criteria="Existing run remains separate",
                    status="completed",
                    kind="standard",
                )
            )
            await session.commit()

    asyncio.run(seed_standard_run())

    response = test_client.post("/api/demo/seed")

    assert response.status_code == 200
    payload = response.json()
    assert payload["created_runs"] == 2
    assert payload["message"] == "Demo benchmark data created."
    counts = asyncio.run(_count_demo_data(session_factory))
    assert counts["standard_runs"] == 1
    assert counts["benchmark_runs"] == 2


def test_repeated_seed_call_does_not_duplicate_demo_benchmark_data(client):
    test_client, session_factory = client

    first = test_client.post("/api/demo/seed")
    second = test_client.post("/api/demo/seed")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["created_runs"] == 0
    counts = asyncio.run(_count_demo_data(session_factory))
    assert counts["suites"] == 1
    assert counts["cases"] == 2
    assert counts["benchmark_runs"] == 2


def test_existing_benchmark_demo_data_returns_created_runs_zero(client):
    test_client, _session_factory = client

    test_client.post("/api/demo/seed")
    response = test_client.post("/api/demo/seed")

    assert response.status_code == 200
    assert response.json() == {
        "created_runs": 0,
        "created_suites": 0,
        "created_cases": 0,
        "message": "No new demo data was created. Demo benchmark data already exists for this account.",
    }
