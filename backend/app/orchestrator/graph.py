from __future__ import annotations

import json
import logging
import time
from contextvars import ContextVar
from typing import Any
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents import executor, judge, planner
from app.core.telemetry import begin_capture, end_capture
from app.models.domain import Escalation, LedgerEntry, Run, Task, TaskAttempt
from app.orchestrator.states import VerifyFlowState
from app.registry.base import registry
from app.registry.verifiers import browser as _browser_verifiers  # noqa: F401
from app.registry.verifiers import filesystem as _filesystem_verifiers  # noqa: F401
from app.registry.verifiers import github as _github_verifiers  # noqa: F401
from app.schemas.verification import VerificationResult
from app.services import reliability

_db_session: ContextVar[AsyncSession] = ContextVar("verifyflow_graph_db")
logger = logging.getLogger(__name__)


def _get_db() -> AsyncSession:
    return _db_session.get()


def _get_settings():
    from app.core.config import settings

    return settings


def _serialize_task(task: Task) -> dict[str, Any]:
    return {
        "id": str(task.id),
        "run_id": str(task.run_id),
        "index": task.index,
        "description": task.description,
        "success_criteria": task.success_criteria,
        "tool_name": task.tool_name,
        "tool_params": task.tool_params,
        "status": task.status,
        "claimed_result": task.claimed_result,
        "retry_count": task.retry_count,
        "created_at": task.created_at.isoformat(),
    }


def _serialize_run(run: Run) -> VerifyFlowState:
    tasks = [_serialize_task(task) for task in run.tasks]
    return {
        "run_id": str(run.id),
        "goal": run.goal,
        "acceptance_criteria": run.acceptance_criteria,
        "tasks": tasks,
        "current_task_index": -1,
        "current_task": None,
        "current_attempt_id": None,
        "action_claim": None,
        "verification_result": None,
        "executor_telemetry": [],
        "verifier_telemetry": [],
        "retry_count": 0,
        "error": None,
    }


async def _load_run(db: AsyncSession, run_id: str) -> Run:
    result = await db.execute(
        select(Run)
        .options(selectinload(Run.tasks))
        .where(Run.id == UUID(run_id))
    )
    run = result.scalar_one()
    run.tasks.sort(key=lambda task: task.index)
    return run


async def _load_task(db: AsyncSession, task_id: str) -> Task:
    result = await db.execute(select(Task).where(Task.id == UUID(task_id)))
    return result.scalar_one()


async def _refresh_tasks(state: VerifyFlowState) -> list[dict[str, Any]]:
    db = _get_db()
    result = await db.execute(
        select(Task)
        .where(Task.run_id == UUID(state["run_id"]))
        .order_by(Task.index.asc())
    )
    tasks = result.scalars().all()
    return [_serialize_task(task) for task in tasks]


async def _create_ledger_entry(
    task: Task,
    result: dict[str, Any],
    *,
    attempt_id: str | None = None,
) -> None:
    db = _get_db()
    entry = LedgerEntry(
        task_id=task.id,
        run_id=task.run_id,
        attempt_id=UUID(attempt_id) if attempt_id else None,
        verification_method=result["method"],
        confidence=result["confidence"],
        verified=result["verified"],
        evidence=result["evidence"],
        judge_reasoning=result.get("judge_reasoning"),
    )
    db.add(entry)
    await db.commit()
    logger.info(
        "Ledger entry created for run=%s task=%s method=%s verified=%s confidence=%.2f",
        task.run_id,
        task.id,
        result["method"],
        result["verified"],
        result["confidence"],
    )


async def plan_node(state: VerifyFlowState) -> VerifyFlowState:
    db = _get_db()
    run = await _load_run(db, state["run_id"])
    run.status = "planning"
    await db.commit()
    await db.refresh(run)
    logger.info("Run %s entering plan node", state["run_id"])

    planned_state = await planner.plan(state, db)
    planned_state["tasks"] = await _refresh_tasks(state)
    planned_state["current_attempt_id"] = None
    planned_state["executor_telemetry"] = []
    planned_state["verifier_telemetry"] = []
    logger.info("Run %s planned %s task(s)", state["run_id"], len(planned_state["tasks"]))
    return planned_state


async def pick_task_node(state: VerifyFlowState) -> VerifyFlowState:
    tasks = await _refresh_tasks(state)
    next_task = next((task for task in tasks if task["status"] == "pending"), None)

    if next_task is None:
        logger.info("Run %s found no pending tasks; routing to finish", state["run_id"])
        return {
            **state,
            "tasks": tasks,
            "current_task": None,
            "action_claim": None,
            "verification_result": None,
            "error": None,
        }

    logger.info(
        "Run %s picked task %s (index=%s, status=%s)",
        state["run_id"],
        next_task["id"],
        next_task["index"],
        next_task["status"],
    )
    return {
        **state,
        "tasks": tasks,
        "current_task_index": next_task["index"],
        "current_task": next_task,
        "current_attempt_id": None,
        "action_claim": None,
        "verification_result": None,
        "executor_telemetry": [],
        "verifier_telemetry": [],
        "retry_count": next_task["retry_count"],
        "error": None,
    }


async def execute_node(state: VerifyFlowState) -> VerifyFlowState:
    db = _get_db()
    current_task = state["current_task"]
    if current_task is None:
        return {**state, "error": "No current task selected."}

    task = await _load_task(db, current_task["id"])
    task.status = "executing"
    await db.commit()
    attempt = await reliability.start_task_attempt(
        db,
        run_id=state["run_id"],
        task=task,
        tool_params=current_task.get("tool_params", {}) or {},
    )
    logger.info(
        "Run %s executing task %s with tool %s",
        state["run_id"],
        current_task["id"],
        current_task["tool_name"],
    )

    capture_token = begin_capture()
    started_at = time.perf_counter()
    updated_state = await executor.execute({**state, "current_attempt_id": str(attempt.id)}, db)
    executor_telemetry = end_capture(capture_token)
    executor_latency_ms = (time.perf_counter() - started_at) * 1000
    await reliability.finalize_executor_attempt(
        db,
        attempt_id=str(attempt.id),
        action_claim=updated_state["action_claim"] or {},
        executor_latency_ms=executor_latency_ms,
        telemetry_events=executor_telemetry,
    )
    await reliability.refresh_run_telemetry(db, state["run_id"])
    tasks = await _refresh_tasks(updated_state)
    current_task = next(task_data for task_data in tasks if task_data["id"] == current_task["id"])
    return {
        **updated_state,
        "tasks": tasks,
        "current_task": current_task,
        "current_attempt_id": str(attempt.id),
        "executor_telemetry": executor_telemetry,
    }


async def verify_node(state: VerifyFlowState) -> VerifyFlowState:
    db = _get_db()
    current_task_data = state["current_task"]
    action_claim = state["action_claim"]
    if current_task_data is None or action_claim is None:
        return {**state, "error": "No current task or action claim available for verification."}

    task = await _load_task(db, current_task_data["id"])
    task.status = "claimed"
    await db.commit()
    logger.info(
        "Run %s verifying task %s claimed_success=%s",
        state["run_id"],
        current_task_data["id"],
        action_claim.get("claimed_success"),
    )

    started_at = time.perf_counter()
    verification_result = await registry.verify(action_claim)
    verification_payload = verification_result.model_dump()
    verifier_latency_ms = (time.perf_counter() - started_at) * 1000
    await _create_ledger_entry(task, verification_payload, attempt_id=state.get("current_attempt_id"))
    await reliability.finalize_verification_attempt(
        db,
        attempt_id=state.get("current_attempt_id"),
        verification_payload=verification_payload,
        verifier_latency_ms=verifier_latency_ms,
        telemetry_events=[],
        outcome="deterministic_verification",
    )
    await reliability.refresh_run_telemetry(db, state["run_id"])
    logger.info(
        "Run %s deterministic verification for task %s => verified=%s confidence=%.2f",
        state["run_id"],
        current_task_data["id"],
        verification_payload["verified"],
        verification_payload["confidence"],
    )

    tasks = await _refresh_tasks(state)
    current_task = next(task_data for task_data in tasks if task_data["id"] == current_task_data["id"])
    return {
        **state,
        "tasks": tasks,
        "current_task": current_task,
        "verification_result": verification_payload,
        "verifier_telemetry": [],
        "error": None,
    }


async def judge_node(state: VerifyFlowState) -> VerifyFlowState:
    db = _get_db()
    current_task = state["current_task"]
    if current_task is None:
        return {**state, "error": "No current task available for judging."}

    task = await _load_task(db, current_task["id"])
    task.status = "claimed"
    await db.commit()
    logger.info("Run %s routing task %s to judge", state["run_id"], current_task["id"])

    capture_token = begin_capture()
    started_at = time.perf_counter()
    updated_state = await judge.evaluate(state, db)
    verifier_telemetry = end_capture(capture_token)
    verifier_latency_ms = (time.perf_counter() - started_at) * 1000
    await reliability.finalize_verification_attempt(
        db,
        attempt_id=state.get("current_attempt_id"),
        verification_payload=updated_state["verification_result"] or {},
        verifier_latency_ms=verifier_latency_ms,
        telemetry_events=verifier_telemetry,
        outcome="judge_verification",
    )
    await reliability.refresh_run_telemetry(db, state["run_id"])
    tasks = await _refresh_tasks(state)
    current_task = next(task_data for task_data in tasks if task_data["id"] == current_task["id"])
    return {
        **updated_state,
        "tasks": tasks,
        "current_task": current_task,
        "verifier_telemetry": verifier_telemetry,
        "error": None,
    }


async def decide_node(state: VerifyFlowState) -> VerifyFlowState:
    db = _get_db()
    current_task = state["current_task"]
    verification_result = state["verification_result"]

    if current_task is None or verification_result is None:
        return {**state, "error": "Cannot decide without a task and verification result."}

    task = await _load_task(db, current_task["id"])
    settings = _get_settings()

    if verification_result["verified"] and verification_result["confidence"] >= settings.verification_confidence_threshold:
        task.status = "verified"
        await db.commit()
        next_retry_count = task.retry_count
        attempt_result = await db.execute(
            select(TaskAttempt).where(TaskAttempt.id == UUID(state["current_attempt_id"]))
        ) if state.get("current_attempt_id") else None
        attempt = attempt_result.scalar_one_or_none() if attempt_result is not None else None
        if attempt is not None:
            attempt.outcome = "verified"
            await db.commit()
        logger.info(
            "Run %s task %s verified at confidence %.2f",
            state["run_id"],
            current_task["id"],
            verification_result["confidence"],
        )
    elif state["retry_count"] < settings.max_retries:
        task.retry_count += 1
        await db.commit()
        next_retry_count = task.retry_count
        attempt_result = await db.execute(
            select(TaskAttempt).where(TaskAttempt.id == UUID(state["current_attempt_id"]))
        ) if state.get("current_attempt_id") else None
        attempt = attempt_result.scalar_one_or_none() if attempt_result is not None else None
        if attempt is not None:
            attempt.outcome = "retrying"
            await db.commit()
        logger.info(
            "Run %s task %s failed verification; retrying (%s/%s)",
            state["run_id"],
            current_task["id"],
            next_retry_count,
            settings.max_retries,
        )
    else:
        await db.commit()
        next_retry_count = settings.max_retries + 1
        attempt_result = await db.execute(
            select(TaskAttempt).where(TaskAttempt.id == UUID(state["current_attempt_id"]))
        ) if state.get("current_attempt_id") else None
        attempt = attempt_result.scalar_one_or_none() if attempt_result is not None else None
        if attempt is not None:
            attempt.outcome = "escalating"
            await db.commit()
        logger.info(
            "Run %s task %s exhausted retries; escalating",
            state["run_id"],
            current_task["id"],
        )

    tasks = await _refresh_tasks(state)
    current_task = next((task_data for task_data in tasks if task_data["id"] == current_task["id"]), None)

    return {
        **state,
        "tasks": tasks,
        "current_task": current_task,
        "retry_count": next_retry_count,
        "error": None,
    }


async def escalate_node(state: VerifyFlowState) -> VerifyFlowState:
    db = _get_db()
    current_task = state["current_task"]
    settings = _get_settings()
    verification_result = state["verification_result"] or {}

    if current_task is None:
        return {**state, "error": "No current task available to escalate."}

    task = await _load_task(db, current_task["id"])
    task.status = "escalated"
    await db.commit()
    logger.info("Run %s task %s escalated", state["run_id"], current_task["id"])

    evidence = (
        f"Escalated after {settings.max_retries} retries. "
        f"Last judge reasoning: {verification_result.get('judge_reasoning')}"
    )
    escalation = await reliability.create_escalation(
        db,
        run_id=state["run_id"],
        task_id=current_task["id"],
        failure_reason=evidence,
        evidence_bundle={
            "goal": state["goal"],
            "task": current_task,
            "action_claim": state.get("action_claim"),
            "verification_result": verification_result,
            "executor_telemetry": state.get("executor_telemetry", []),
            "verifier_telemetry": state.get("verifier_telemetry", []),
        },
    )
    escalation_result = {
        "verified": False,
        "confidence": 0.0,
        "method": "hybrid",
        "evidence": evidence,
        "judge_reasoning": verification_result.get("judge_reasoning"),
    }
    await _create_ledger_entry(task, escalation_result, attempt_id=state.get("current_attempt_id"))
    attempt_result = await db.execute(
        select(TaskAttempt).where(TaskAttempt.id == UUID(state["current_attempt_id"]))
    ) if state.get("current_attempt_id") else None
    attempt = attempt_result.scalar_one_or_none() if attempt_result is not None else None
    if attempt is not None:
        attempt.outcome = "escalated"
        await db.commit()
    await reliability.refresh_run_telemetry(db, state["run_id"])

    if db.bind is not None and db.bind.dialect.name == "postgresql":
        payload = {
            "run_id": state["run_id"],
            "task_id": current_task["id"],
            "evidence": evidence,
            "escalation_id": str(escalation.id),
        }
        await db.execute(
            text("SELECT pg_notify('task_escalated', :payload)"),
            {"payload": json.dumps(payload)},
        )
        await db.commit()

    tasks = await _refresh_tasks(state)
    return {
        **state,
        "tasks": tasks,
        "current_task": None,
        "current_attempt_id": None,
        "action_claim": None,
        "verification_result": None,
        "error": None,
    }


async def finish_node(state: VerifyFlowState) -> VerifyFlowState:
    db = _get_db()
    run = await _load_run(db, state["run_id"])
    tasks = await _refresh_tasks(state)
    task_statuses = {task["status"] for task in tasks}
    if not tasks or "escalated" in task_statuses or task_statuses - {"verified"}:
        run.status = "failed"
        logger.info(
            "Run %s finished in failed state because tasks were incomplete or missing: %s",
            state["run_id"],
            sorted(task_statuses) if task_statuses else ["<none>"],
        )
    else:
        run.status = "completed"
        logger.info("Run %s completed", state["run_id"])
    await db.commit()
    await reliability.refresh_run_telemetry(db, state["run_id"])

    return {
        **state,
        "tasks": tasks,
        "current_task": None,
        "current_attempt_id": None,
        "action_claim": None,
        "verification_result": None,
        "error": None,
    }


def route_after_pick_task(state: VerifyFlowState) -> str:
    return "execute" if state["current_task"] is not None else "finish"


def route_after_verify(state: VerifyFlowState) -> str:
    result = state["verification_result"]
    if result is None:
        return "judge"
    verification_result = VerificationResult.model_validate(result)
    return "judge" if registry.needs_judge(verification_result) else "decide"


def route_after_decide(state: VerifyFlowState) -> str:
    settings = _get_settings()
    result = state["verification_result"] or {}
    if result.get("verified") and result.get("confidence", 0.0) >= settings.verification_confidence_threshold:
        return "pick_task"
    if state["retry_count"] <= settings.max_retries:
        return "execute"
    return "escalate"


graph = StateGraph(VerifyFlowState)
graph.add_node("plan", plan_node)
graph.add_node("pick_task", pick_task_node)
graph.add_node("execute", execute_node)
graph.add_node("verify", verify_node)
graph.add_node("judge", judge_node)
graph.add_node("decide", decide_node)
graph.add_node("escalate", escalate_node)
graph.add_node("finish", finish_node)

graph.add_edge(START, "plan")
graph.add_edge("plan", "pick_task")
graph.add_conditional_edges("pick_task", route_after_pick_task, {"execute": "execute", "finish": "finish"})
graph.add_edge("execute", "verify")
graph.add_conditional_edges("verify", route_after_verify, {"judge": "judge", "decide": "decide"})
graph.add_edge("judge", "decide")
graph.add_conditional_edges(
    "decide",
    route_after_decide,
    {"pick_task": "pick_task", "execute": "execute", "escalate": "escalate"},
)
graph.add_edge("escalate", "finish")
graph.add_edge("finish", END)

app = graph.compile()


async def run_graph(run_id: str, db: AsyncSession) -> None:
    run = await _load_run(db, run_id)
    initial_state = _serialize_run(run)
    token = _db_session.set(db)
    try:
        logger.info("Starting graph execution for run %s", run_id)
        await app.ainvoke(initial_state)
        logger.info("Finished graph execution for run %s", run_id)
    finally:
        await executor.reset_browser_clients()
        _db_session.reset(token)
