from __future__ import annotations

import os
from uuid import UUID, uuid4
from unittest.mock import AsyncMock

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
from app.models.domain import Escalation, LedgerEntry, Run, RunTelemetry, Task, TaskAttempt
from app.orchestrator import graph as graph_module
from app.orchestrator.graph import decide_node, run_graph
from app.services import reliability


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


@pytest.mark.asyncio
async def test_decide_node_resets_retryable_task_to_pending(monkeypatch: pytest.MonkeyPatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    run_id = uuid4()
    async with session_factory() as session:
        run = Run(
            id=run_id,
            goal="Retry a transient failure",
            acceptance_criteria="Task should reset to pending before retry",
            status="executing",
        )
        task = Task(
            run_id=run_id,
            index=0,
            description="Transiently flaky task",
            success_criteria="Eventually succeeds",
            tool_name="browser.click",
            tool_params={"selector": "button"},
            status="claimed",
            retry_count=0,
        )
        session.add(run)
        session.add(task)
        await session.commit()
        await session.refresh(task)

        attempt = await reliability.start_task_attempt(
            session,
            run_id=str(run_id),
            task=task,
            tool_params=task.tool_params,
        )

        state = {
            "run_id": str(run_id),
            "goal": run.goal,
            "acceptance_criteria": run.acceptance_criteria,
            "tasks": [],
            "current_task_index": task.index,
            "current_task": graph_module._serialize_task(task),
            "current_attempt_id": str(attempt.id),
            "action_claim": {
                "tool_name": task.tool_name,
                "params": task.tool_params,
                "claimed_success": False,
                "error": "Request timeout while waiting for page response.",
            },
            "verification_result": {
                "verified": False,
                "confidence": 0.2,
                "method": "deterministic",
                "evidence": "Timeout while verifying page content.",
            },
            "executor_telemetry": [],
            "verifier_telemetry": [],
            "retry_count": 0,
            "decision": None,
            "retryable": True,
            "escalation_reason": None,
            "error": None,
        }

        token = graph_module._db_session.set(session)
        try:
            updated = await decide_node(state)
        finally:
            graph_module._db_session.reset(token)

        await session.refresh(task)
        await session.refresh(attempt)

        assert task.status == "pending"
        assert task.retry_count == 1
        assert attempt.outcome == "retrying"
        assert updated["decision"] == "execute"
        assert updated["retryable"] is True

    await engine.dispose()


@pytest.mark.asyncio
async def test_run_graph_escalates_unrecoverable_failure_without_retries(monkeypatch: pytest.MonkeyPatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    verify_mock = AsyncMock(
        return_value=graph_module.VerificationResult(
            verified=False,
            confidence=0.1,
            method="deterministic",
            evidence="Element not found while attempting click.",
        )
    )
    execute_mock = AsyncMock(
        side_effect=lambda state, db: {
            **state,
            "action_claim": {
                "tool_name": state["current_task"]["tool_name"],
                "params": state["current_task"]["tool_params"],
                "result": None,
                "claimed_success": False,
                "claimed_at": "now",
                "error": "Element not found",
            },
            "error": "Element not found",
        }
    )
    monkeypatch.setattr(graph_module.registry, "verify", verify_mock)
    monkeypatch.setattr(graph_module.registry, "needs_judge", lambda result: False)
    monkeypatch.setattr(graph_module.executor, "reset_browser_clients", AsyncMock())
    monkeypatch.setattr(graph_module.executor, "execute", execute_mock)

    run_id = uuid4()
    async with session_factory() as session:
        run = Run(
            id=run_id,
            goal="Stop immediately on unrecoverable failure",
            acceptance_criteria="Task escalates once without retry churn",
            status="pending",
        )
        task = Task(
            run_id=run_id,
            index=0,
            description="Click a missing element",
            success_criteria="Element exists",
            tool_name="browser.click",
            tool_params={"selector": "text=English"},
            status="pending",
        )
        session.add(run)
        session.add(task)
        await session.commit()

        await run_graph(str(run_id), session)

        await session.refresh(run)
        await session.refresh(task)

        attempts = (await session.execute(select(TaskAttempt).where(TaskAttempt.task_id == task.id))).scalars().all()
        escalations = (await session.execute(select(Escalation).where(Escalation.task_id == task.id))).scalars().all()

        assert run.status == "failed"
        assert task.status == "escalated"
        assert task.retry_count == 0
        assert execute_mock.await_count == 1
        assert len(attempts) == 1
        assert attempts[0].outcome == "escalated"
        assert len(escalations) == 1
        assert "Element not found" in escalations[0].failure_reason

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_ledger_entry_skips_duplicate_attempt_results():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    run_id = uuid4()
    async with session_factory() as session:
        run = Run(
            id=run_id,
            goal="Prevent duplicate ledger noise",
            acceptance_criteria="Only one ledger row is stored per identical attempt result",
            status="pending",
        )
        task = Task(
            run_id=run_id,
            index=0,
            description="Verify once",
            success_criteria="Single deterministic record",
            tool_name="filesystem.read_file",
            tool_params={"path": "C:/tmp/demo.txt"},
            status="pending",
        )
        session.add(run)
        session.add(task)
        await session.commit()
        await session.refresh(task)

        attempt = await reliability.start_task_attempt(
            session,
            run_id=str(run_id),
            task=task,
            tool_params=task.tool_params,
        )

        token = graph_module._db_session.set(session)
        try:
            payload = {
                "verified": False,
                "confidence": 0.7,
                "method": "deterministic",
                "evidence": "Expected text was not present.",
                "judge_reasoning": None,
            }
            await graph_module._create_ledger_entry(task, payload, attempt_id=str(attempt.id))
            await graph_module._create_ledger_entry(task, payload, attempt_id=str(attempt.id))
        finally:
            graph_module._db_session.reset(token)

        entries = (await session.execute(select(LedgerEntry).where(LedgerEntry.task_id == task.id))).scalars().all()
        assert len(entries) == 1

    await engine.dispose()


@pytest.mark.asyncio
async def test_verify_node_treats_transient_verifier_exception_as_retryable(monkeypatch: pytest.MonkeyPatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    monkeypatch.setattr(
        graph_module.registry,
        "verify",
        AsyncMock(side_effect=TimeoutError("Timed out while querying GitHub for verifier evidence")),
    )

    run_id = uuid4()
    async with session_factory() as session:
        run = Run(
            id=run_id,
            goal="Retry transient verifier failures",
            acceptance_criteria="Transient verifier errors should retry instead of escalating immediately",
            status="executing",
        )
        task = Task(
            run_id=run_id,
            index=0,
            description="Check GitHub file state",
            success_criteria="Verifier reads repository state",
            tool_name="github.get_file",
            tool_params={"repo": "demo/repo", "path": "README.md"},
            status="executing",
            retry_count=0,
        )
        session.add(run)
        session.add(task)
        await session.commit()
        await session.refresh(task)

        attempt = await reliability.start_task_attempt(
            session,
            run_id=str(run_id),
            task=task,
            tool_params=task.tool_params,
        )
        await reliability.finalize_executor_attempt(
            session,
            attempt_id=str(attempt.id),
            action_claim={
                "tool_name": task.tool_name,
                "params": task.tool_params,
                "claimed_success": True,
                "result": {"path": "README.md"},
            },
            executor_latency_ms=10.0,
            telemetry_events=[],
        )

        state = {
            "run_id": str(run_id),
            "goal": run.goal,
            "acceptance_criteria": run.acceptance_criteria,
            "tasks": [graph_module._serialize_task(task)],
            "current_task_index": task.index,
            "current_task": graph_module._serialize_task(task),
            "current_attempt_id": str(attempt.id),
            "action_claim": {
                "tool_name": task.tool_name,
                "params": task.tool_params,
                "claimed_success": True,
                "result": {"path": "README.md"},
            },
            "verification_result": None,
            "executor_telemetry": [],
            "verifier_telemetry": [],
            "retry_count": 0,
            "decision": None,
            "retryable": True,
            "escalation_reason": None,
            "error": None,
        }

        token = graph_module._db_session.set(session)
        try:
            verified_state = await graph_module.verify_node(state)
            next_hop = graph_module.route_after_verify(verified_state)
            decided_state = await decide_node(verified_state)
        finally:
            graph_module._db_session.reset(token)

        await session.refresh(task)
        await session.refresh(attempt)

        assert verified_state["verification_result"]["error_details"]["retryable"] is True
        assert verified_state["verification_result"]["error_details"]["category"] == "timeout"
        assert verified_state["verification_result"]["outcome"] == "inconclusive"
        assert next_hop == "decide"
        assert decided_state["decision"] == "execute"
        assert task.status == "pending"
        assert task.retry_count == 1
        assert attempt.outcome == "retrying"

    await engine.dispose()


@pytest.mark.asyncio
async def test_verify_node_treats_unrecoverable_verifier_exception_as_terminal(monkeypatch: pytest.MonkeyPatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    monkeypatch.setattr(
        graph_module.registry,
        "verify",
        AsyncMock(side_effect=PermissionError("Permission denied while reading verifier-side repository state")),
    )

    run_id = uuid4()
    async with session_factory() as session:
        run = Run(
            id=run_id,
            goal="Stop on terminal verifier failures",
            acceptance_criteria="Verifier-side permission failures should not loop through retries",
            status="executing",
        )
        task = Task(
            run_id=run_id,
            index=0,
            description="Check restricted GitHub file state",
            success_criteria="Verifier can access repository state",
            tool_name="github.get_file",
            tool_params={"repo": "demo/private-repo", "path": "README.md"},
            status="executing",
            retry_count=0,
        )
        session.add(run)
        session.add(task)
        await session.commit()
        await session.refresh(task)

        attempt = await reliability.start_task_attempt(
            session,
            run_id=str(run_id),
            task=task,
            tool_params=task.tool_params,
        )
        await reliability.finalize_executor_attempt(
            session,
            attempt_id=str(attempt.id),
            action_claim={
                "tool_name": task.tool_name,
                "params": task.tool_params,
                "claimed_success": True,
                "result": {"path": "README.md"},
            },
            executor_latency_ms=10.0,
            telemetry_events=[],
        )

        state = {
            "run_id": str(run_id),
            "goal": run.goal,
            "acceptance_criteria": run.acceptance_criteria,
            "tasks": [graph_module._serialize_task(task)],
            "current_task_index": task.index,
            "current_task": graph_module._serialize_task(task),
            "current_attempt_id": str(attempt.id),
            "action_claim": {
                "tool_name": task.tool_name,
                "params": task.tool_params,
                "claimed_success": True,
                "result": {"path": "README.md"},
            },
            "verification_result": None,
            "executor_telemetry": [],
            "verifier_telemetry": [],
            "retry_count": 0,
            "decision": None,
            "retryable": True,
            "escalation_reason": None,
            "error": None,
        }

        token = graph_module._db_session.set(session)
        try:
            verified_state = await graph_module.verify_node(state)
            next_hop = graph_module.route_after_verify(verified_state)
            decided_state = await decide_node(verified_state)
        finally:
            graph_module._db_session.reset(token)

        await session.refresh(task)
        await session.refresh(attempt)

        assert verified_state["verification_result"]["error_details"]["retryable"] is False
        assert verified_state["verification_result"]["error_details"]["category"] == "verification_error"
        assert next_hop == "decide"
        assert decided_state["decision"] == "escalate"
        assert decided_state["retryable"] is False
        assert task.status == "failed"
        assert task.retry_count == 0
        assert attempt.outcome == "escalating"

    await engine.dispose()


@pytest.mark.asyncio
async def test_run_graph_persists_structured_failure_record_for_catastrophic_crash(monkeypatch: pytest.MonkeyPatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def planner_stub(state, db):
        task = Task(
            run_id=UUID(state["run_id"]),
            index=0,
            description="Task that will crash during execution",
            success_criteria="Execution should persist catastrophic evidence",
            tool_name="browser.click",
            tool_params={"selector": "text=English"},
            status="pending",
        )
        db.add(task)
        await db.commit()
        refreshed_run = await graph_module._load_run(db, state["run_id"])
        return {
            **state,
            "tasks": [graph_module._serialize_task(item) for item in refreshed_run.tasks],
        }

    monkeypatch.setattr(graph_module.planner, "plan", planner_stub)
    monkeypatch.setattr(graph_module.executor, "reset_browser_clients", AsyncMock())
    monkeypatch.setattr(
        graph_module.executor,
        "execute",
        AsyncMock(side_effect=RuntimeError("Executor process crashed unexpectedly")),
    )

    run_id = uuid4()
    async with session_factory() as session:
        run = Run(
            id=run_id,
            goal="Persist graph crash evidence",
            acceptance_criteria="Catastrophic failures should remain debuggable",
            status="pending",
        )
        session.add(run)
        await session.commit()

        with pytest.raises(RuntimeError, match="Executor process crashed unexpectedly"):
            await run_graph(str(run_id), session)

        refreshed_run = (await session.execute(select(Run).where(Run.id == run_id))).scalar_one()
        tasks = (await session.execute(select(Task).where(Task.run_id == run_id))).scalars().all()
        attempts = (await session.execute(select(TaskAttempt).where(TaskAttempt.run_id == run_id))).scalars().all()
        escalations = (await session.execute(select(Escalation).where(Escalation.run_id == run_id))).scalars().all()
        telemetry = (await session.execute(select(RunTelemetry).where(RunTelemetry.run_id == run_id))).scalar_one()
        ledger_entries = (await session.execute(select(LedgerEntry).where(LedgerEntry.run_id == run_id))).scalars().all()

        assert refreshed_run.status == "failed"
        assert refreshed_run.failure_record is not None
        assert refreshed_run.failure_record["category"] == "catastrophic_orchestration_failure"
        assert refreshed_run.failure_record["exception_type"] == "RuntimeError"
        assert "Executor process crashed unexpectedly" in refreshed_run.failure_record["message"]
        assert len(tasks) == 1
        assert tasks[0].status == "escalated"
        assert tasks[0].claimed_result["catastrophic_failure"]["category"] == "catastrophic_orchestration_failure"
        assert len(attempts) == 1
        assert attempts[0].outcome == "escalated"
        assert attempts[0].verification_payload["outcome"] == "catastrophic_failure"
        assert len(escalations) == 1
        assert escalations[0].status == "pending_review"
        assert escalations[0].evidence_bundle["exception_type"] == "RuntimeError"
        assert len(ledger_entries) == 1
        assert "Catastrophic orchestration failure" in ledger_entries[0].evidence
        assert telemetry.hybrid_verifications == 1

    await engine.dispose()
