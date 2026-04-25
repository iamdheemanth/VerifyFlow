from __future__ import annotations

import os
from pathlib import Path
from tempfile import mkstemp
from uuid import UUID, uuid4

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
from app.models.domain import (
    BenchmarkCase,
    BenchmarkSuite,
    Escalation,
    LedgerEntry,
    ModelPromptConfig,
    ReviewerDecision,
    Run,
    RunTelemetry,
    Task,
    TaskAttempt,
)


def _sqlite_url() -> tuple[str, Path]:
    fd, raw_path = mkstemp(suffix=".db")
    os.close(fd)
    path = Path(raw_path)
    return f"sqlite+aiosqlite:///{path.as_posix()}", path


async def _seed_contract_data(session: AsyncSession) -> dict[str, UUID]:
    executor_config = ModelPromptConfig(
        id=uuid4(),
        role="executor",
        name="Executor A",
        model_name="openrouter/executor",
        prompt_template="Executor prompt",
        prompt_version="v1",
    )
    judge_config = ModelPromptConfig(
        id=uuid4(),
        role="judge",
        name="Judge A",
        model_name="openrouter/judge",
        prompt_template="Judge prompt",
        prompt_version="v1",
    )
    suite = BenchmarkSuite(id=uuid4(), name="Smoke suite", description="Contract coverage suite")
    case = BenchmarkCase(
        id=uuid4(),
        suite_id=suite.id,
        name="Wikipedia English",
        goal="Navigate to wikipedia and click English",
        acceptance_criteria="English main page is shown",
        expected_outcome="completed",
        label_data={"expected_verified": False},
    )
    run = Run(
        id=uuid4(),
        owner_subject="test-user",
        owner_email="test@example.com",
        goal="Navigate to wikipedia and click English",
        acceptance_criteria="English main page is shown",
        status="failed",
        kind="benchmark",
        latest_confidence=0.7,
        executor_config_id=executor_config.id,
        judge_config_id=judge_config.id,
        benchmark_suite_id=suite.id,
        benchmark_case_id=case.id,
    )
    task = Task(
        id=uuid4(),
        run_id=run.id,
        index=0,
        description="Click the English language link.",
        success_criteria="The destination page contains The Free Encyclopedia",
        tool_name="browser.click",
        tool_params={"selector": "text=English"},
        status="escalated",
        claimed_result={"claimed_success": False, "error": "Element not found"},
        retry_count=3,
    )
    attempt = TaskAttempt(
        id=uuid4(),
        run_id=run.id,
        task_id=task.id,
        attempt_index=0,
        tool_name="browser.click",
        tool_params={"selector": "text=English"},
        action_claim={"claimed_success": False, "error": "Element not found"},
        verification_payload={"outcome": "execution_failed", "summary": "Click failed before evidence could be collected."},
        execution_steps=[{"step": "click", "status": "failed"}],
        tool_calls=[{"tool": "browser.click"}],
        claimed_success=False,
        verification_method="deterministic",
        final_confidence=0.7,
        executor_latency_ms=30,
        verifier_latency_ms=5,
        total_latency_ms=35,
        token_input=0,
        token_output=0,
        token_total=0,
        estimated_cost_usd=0.0,
        outcome="escalated",
        error="Element not found",
    )
    telemetry = RunTelemetry(
        id=uuid4(),
        run_id=run.id,
        total_executor_latency_ms=30,
        total_verifier_latency_ms=5,
        total_task_latency_ms=35,
        total_retry_count=3,
        total_token_input=0,
        total_token_output=0,
        total_token_total=0,
        total_estimated_cost_usd=0.0,
        total_tool_calls=1,
        deterministic_verifications=1,
        llm_judge_verifications=0,
        hybrid_verifications=1,
        average_confidence=0.7,
    )
    escalation = Escalation(
        id=uuid4(),
        run_id=run.id,
        task_id=task.id,
        status="pending_review",
        failure_reason="Element not found",
        evidence_bundle={"summary": "The click target never resolved."},
    )
    decision = ReviewerDecision(
        id=uuid4(),
        escalation_id=escalation.id,
        run_id=run.id,
        task_id=task.id,
        reviewer_key="qa-1",
        reviewer_display_name="QA One",
        reviewer_name="QA One",
        decision="send_back",
        notes="Retry with fallback navigation.",
    )
    ledger_entry = LedgerEntry(
        id=uuid4(),
        run_id=run.id,
        task_id=task.id,
        attempt_id=attempt.id,
        verification_method="deterministic",
        confidence=0.7,
        verified=False,
        evidence="Browser click action claimed successful. Routing to judge.",
        judge_reasoning=None,
    )

    session.add_all(
        [
            executor_config,
            judge_config,
            suite,
            case,
            run,
            task,
            attempt,
            telemetry,
            escalation,
            decision,
            ledger_entry,
        ]
    )
    await session.commit()
    return {
        "run_id": run.id,
        "task_id": task.id,
        "suite_id": suite.id,
        "executor_config_id": executor_config.id,
        "escalation_id": escalation.id,
    }


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

    import asyncio

    asyncio.run(setup())
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client, session_factory

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())
    path.unlink(missing_ok=True)


def test_run_inspection_endpoint_returns_grouped_claimed_vs_verified_data(client):
    test_client, session_factory = client

    async def seed():
        async with session_factory() as session:
            return await _seed_contract_data(session)

    import asyncio

    ids = asyncio.run(seed())
    response = test_client.get(f"/api/runs/{ids['run_id']}/inspection")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run"]["id"] == str(ids["run_id"])
    assert payload["claimed_vs_verified"]["total_tasks"] == 1
    assert payload["claimed_vs_verified"]["escalated_tasks"] == 1
    assert payload["task_inspections"][0]["task"]["id"] == str(ids["task_id"])
    assert payload["task_inspections"][0]["latest_claim"]["claimed_success"] is False
    assert payload["task_inspections"][0]["latest_verification"]["outcome"] == "execution_failed"


def test_task_evidence_endpoint_returns_render_ready_payload(client):
    test_client, session_factory = client

    async def seed():
        async with session_factory() as session:
            return await _seed_contract_data(session)

    import asyncio

    ids = asyncio.run(seed())
    response = test_client.get(f"/api/runs/{ids['run_id']}/tasks/{ids['task_id']}/evidence")

    assert response.status_code == 200
    payload = response.json()
    assert payload["task"]["id"] == str(ids["task_id"])
    assert len(payload["attempts"]) == 1
    assert len(payload["ledger_entries"]) == 1
    assert len(payload["escalations"]) == 1
    assert payload["escalations"][0]["reviewer_decisions"][0]["reviewer_key"] == "qa-1"


def test_list_runs_endpoint_returns_normalized_run_summaries(client):
    test_client, session_factory = client

    async def seed():
        async with session_factory() as session:
            return await _seed_contract_data(session)

    import asyncio

    ids = asyncio.run(seed())
    response = test_client.get("/api/runs")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == str(ids["run_id"])
    assert payload[0]["status"] == "failed"
    assert payload[0]["kind"] == "benchmark"
    assert payload[0]["task_count"] == 1


def test_run_endpoint_represents_planning_failure_state(client):
    test_client, session_factory = client

    async def seed():
        async with session_factory() as session:
            run_id = uuid4()
            task_id = uuid4()
            failure_record = {
                "category": "planning_failed",
                "stage": "planning",
                "message": "Planner could not create an executable plan. Manual review is required.",
                "original_goal": "Book a flight to Mars using the travel desk.",
                "acceptance_criteria": "A confirmed itinerary is available.",
                "planner_reason": "Unsupported planner tool_name: travel.book_flight",
                "timestamp": "2026-04-24T12:00:00+00:00",
                "suggested_next_action": "Review the goal and provide a supported filesystem, browser, or GitHub plan before rerunning.",
            }
            run = Run(
                id=run_id,
                owner_subject="test-user",
                owner_email="test@example.com",
                goal=failure_record["original_goal"],
                acceptance_criteria=failure_record["acceptance_criteria"],
                status="failed",
                failure_record=failure_record,
            )
            task = Task(
                id=task_id,
                run_id=run_id,
                index=0,
                description="Planning failed; manual review is required.",
                success_criteria=failure_record["suggested_next_action"],
                tool_name="planner.manual_review",
                tool_params={"planning_failure": failure_record},
                status="escalated",
                claimed_result={"claimed_success": False, "planning_failure": failure_record},
            )
            escalation = Escalation(
                id=uuid4(),
                run_id=run_id,
                task_id=task_id,
                status="pending_review",
                failure_reason=failure_record["message"],
                evidence_bundle=failure_record,
            )
            session.add_all([run, task, escalation])
            await session.commit()
            return run_id

    import asyncio

    run_id = asyncio.run(seed())
    response = test_client.get(f"/api/runs/{run_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["failure_record"]["category"] == "planning_failed"
    assert payload["failure_record"]["original_goal"] == "Book a flight to Mars using the travel desk."
    assert payload["tasks"][0]["status"] == "escalated"
    assert payload["tasks"][0]["tool_name"] == "planner.manual_review"
    assert payload["escalations"][0]["status"] == "pending_review"
    assert payload["escalations"][0]["evidence_bundle"]["planner_reason"] == (
        "Unsupported planner tool_name: travel.book_flight"
    )


def test_benchmark_drilldown_endpoint_returns_overview_and_runs(client):
    test_client, session_factory = client

    async def seed():
        async with session_factory() as session:
            return await _seed_contract_data(session)

    import asyncio

    ids = asyncio.run(seed())
    response = test_client.get(f"/api/benchmarks/suites/{ids['suite_id']}/drilldown")

    assert response.status_code == 200
    payload = response.json()
    assert payload["overview"]["suite_id"] == str(ids["suite_id"])
    assert payload["runs"][0]["run_id"] == str(ids["run_id"])
    assert payload["runs"][0]["retry_count"] == 3


def test_configuration_drilldown_endpoint_returns_run_details(client):
    test_client, session_factory = client

    async def seed():
        async with session_factory() as session:
            return await _seed_contract_data(session)

    import asyncio

    ids = asyncio.run(seed())
    response = test_client.get(f"/api/configurations/{ids['executor_config_id']}/drilldown")

    assert response.status_code == 200
    payload = response.json()
    assert payload["comparison"]["config_id"] == str(ids["executor_config_id"])
    assert payload["runs"][0]["run_id"] == str(ids["run_id"])
    assert payload["runs"][0]["escalation_count"] == 1


def test_missing_run_returns_standardized_error_payload(client):
    test_client, _session_factory = client

    response = test_client.get(f"/api/runs/{uuid4()}")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "run_not_found"
    assert payload["error"]["message"] == "Run not found"


def test_invalid_review_decision_returns_standardized_error_payload(client):
    test_client, session_factory = client

    async def seed():
        async with session_factory() as session:
            return await _seed_contract_data(session)

    import asyncio

    ids = asyncio.run(seed())
    response = test_client.post(
        f"/api/review/escalations/{ids['escalation_id']}/decision",
        json={"decision": "maybe", "reviewer_key": "qa-2", "reviewer_display_name": "QA Two"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_reviewer_decision"
    assert payload["error"]["details"]["decision"] == "maybe"


def test_late_review_decision_on_resolved_escalation_returns_standardized_conflict(client):
    test_client, session_factory = client

    async def seed():
        async with session_factory() as session:
            return await _seed_contract_data(session)

    import asyncio

    ids = asyncio.run(seed())

    first_response = test_client.post(
        f"/api/review/escalations/{ids['escalation_id']}/decision",
        json={"decision": "approve", "reviewer_key": "qa-2", "reviewer_display_name": "QA Two"},
    )
    assert first_response.status_code == 200

    late_response = test_client.post(
        f"/api/review/escalations/{ids['escalation_id']}/decision",
        json={"decision": "reject", "reviewer_key": "qa-3", "reviewer_display_name": "QA Three"},
    )

    assert late_response.status_code == 409
    payload = late_response.json()
    assert payload["error"]["code"] == "escalation_already_resolved"
    assert payload["error"]["message"] == "Escalation has already been resolved"
    assert payload["error"]["details"]["escalation_id"] == str(ids["escalation_id"])
