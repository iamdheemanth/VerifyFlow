from __future__ import annotations

from contextvars import ContextVar
from typing import Any
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents import executor, judge, planner
from app.models.domain import LedgerEntry, Run, Task
from app.orchestrator.states import VerifyFlowState
from app import registry

_db_session: ContextVar[AsyncSession] = ContextVar("verifyflow_graph_db")


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
        "action_claim": None,
        "verification_result": None,
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
    run = await _load_run(db, state["run_id"])
    return [_serialize_task(task) for task in run.tasks]


async def _create_ledger_entry(
    task: Task,
    result: dict[str, Any],
) -> None:
    db = _get_db()
    entry = LedgerEntry(
        task_id=task.id,
        run_id=task.run_id,
        verification_method=result["method"],
        confidence=result["confidence"],
        verified=result["verified"],
        evidence=result["evidence"],
        judge_reasoning=result.get("judge_reasoning"),
    )
    db.add(entry)
    await db.commit()


async def plan_node(state: VerifyFlowState) -> VerifyFlowState:
    db = _get_db()
    run = await _load_run(db, state["run_id"])
    run.status = "planning"
    await db.commit()
    await db.refresh(run)

    planned_state = await planner.plan(state, db)
    planned_state["tasks"] = await _refresh_tasks(state)
    return planned_state


async def pick_task_node(state: VerifyFlowState) -> VerifyFlowState:
    tasks = await _refresh_tasks(state)
    next_task = next((task for task in tasks if task["status"] == "pending"), None)

    if next_task is None:
        return {
            **state,
            "tasks": tasks,
            "current_task": None,
            "action_claim": None,
            "verification_result": None,
            "error": None,
        }

    return {
        **state,
        "tasks": tasks,
        "current_task_index": next_task["index"],
        "current_task": next_task,
        "action_claim": None,
        "verification_result": None,
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

    updated_state = await executor.execute(state, db)
    tasks = await _refresh_tasks(updated_state)
    current_task = next(task_data for task_data in tasks if task_data["id"] == current_task["id"])
    return {
        **updated_state,
        "tasks": tasks,
        "current_task": current_task,
    }


async def verify_node(state: VerifyFlowState) -> VerifyFlowState:
    db = _get_db()
    current_task = state["current_task"]
    if current_task is None:
        return {**state, "error": "No current task available for verification."}

    task = await _load_task(db, current_task["id"])
    task.status = "claimed"
    await db.commit()

    verification_result = await registry.verify(state)
    tasks = await _refresh_tasks(state)
    current_task = next(task_data for task_data in tasks if task_data["id"] == current_task["id"])
    return {
        **state,
        "tasks": tasks,
        "current_task": current_task,
        "verification_result": verification_result,
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

    verification_result = await judge.evaluate(state)
    tasks = await _refresh_tasks(state)
    current_task = next(task_data for task_data in tasks if task_data["id"] == current_task["id"])
    return {
        **state,
        "tasks": tasks,
        "current_task": current_task,
        "verification_result": verification_result,
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
        await _create_ledger_entry(task, verification_result)
    elif verification_result["confidence"] < settings.verification_confidence_threshold and task.retry_count < settings.max_retries:
        task.retry_count += 1
        await db.commit()
    else:
        await db.commit()

    tasks = await _refresh_tasks(state)
    current_task = next((task_data for task_data in tasks if task_data["id"] == current_task["id"]), None)
    retry_count = current_task["retry_count"] if current_task else task.retry_count

    return {
        **state,
        "tasks": tasks,
        "current_task": current_task,
        "retry_count": retry_count,
        "error": None,
    }


async def escalate_node(state: VerifyFlowState) -> VerifyFlowState:
    db = _get_db()
    current_task = state["current_task"]
    verification_result = state["verification_result"] or {
        "verified": False,
        "confidence": 0.0,
        "method": "hybrid",
        "evidence": "Task escalated after retries were exhausted.",
        "judge_reasoning": None,
    }

    if current_task is None:
        return {**state, "error": "No current task available to escalate."}

    task = await _load_task(db, current_task["id"])
    task.status = "escalated"
    await db.commit()
    await _create_ledger_entry(task, verification_result)

    tasks = await _refresh_tasks(state)
    return {
        **state,
        "tasks": tasks,
        "current_task": None,
        "action_claim": None,
        "verification_result": None,
        "error": None,
    }


async def finish_node(state: VerifyFlowState) -> VerifyFlowState:
    db = _get_db()
    run = await _load_run(db, state["run_id"])
    run.status = "completed"
    await db.commit()

    return {
        **state,
        "tasks": await _refresh_tasks(state),
        "current_task": None,
        "action_claim": None,
        "verification_result": None,
        "error": None,
    }


def route_after_pick_task(state: VerifyFlowState) -> str:
    return "execute" if state["current_task"] is not None else "finish"


def route_after_verify(state: VerifyFlowState) -> str:
    result = state["verification_result"] or {}
    method = result.get("method")
    return "judge" if method in {"llm_judge", "hybrid"} else "decide"


def route_after_decide(state: VerifyFlowState) -> str:
    settings = _get_settings()
    result = state["verification_result"] or {}
    if result.get("verified") and result.get("confidence", 0.0) >= settings.verification_confidence_threshold:
        return "pick_task"
    if state["retry_count"] < settings.max_retries:
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
graph.add_edge("escalate", "pick_task")
graph.add_edge("finish", END)

app = graph.compile()


async def run_graph(run_id: str, db: AsyncSession) -> None:
    run = await _load_run(db, run_id)
    initial_state = _serialize_run(run)
    token = _db_session.set(db)
    try:
        await app.ainvoke(initial_state)
    finally:
        _db_session.reset(token)
