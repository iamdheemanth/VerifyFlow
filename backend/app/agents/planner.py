from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Task
from app.orchestrator.states import VerifyFlowState

ALLOWED_TOOL_NAMES = {
    "github.create_file",
    "github.get_file",
    "github.create_pull_request",
    "filesystem.write_file",
    "filesystem.read_file",
    "browser.navigate",
    "browser.fill",
    "browser.click",
}


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


async def plan(state: VerifyFlowState, db: AsyncSession) -> VerifyFlowState:
    if state["tasks"]:
        return {
            **state,
            "tasks": state["tasks"],
            "current_task_index": -1,
            "current_task": None,
            "action_claim": None,
            "verification_result": None,
            "retry_count": 0,
            "error": None,
        }

    from app.core.llm import executor_llm

    planned = await executor_llm.chat_json(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a task planner. Break the user goal into the minimum number "
                    "of discrete, verifiable subtasks. Each task must have a specific "
                    "success criterion that can be checked programmatically or by an observer."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Goal: {state['goal']}\n"
                    f"Acceptance criteria: {state['acceptance_criteria']}"
                ),
            },
        ],
        schema_hint=(
            '{"tasks": [{"description": "str", "success_criteria": "str", '
            '"tool_name": "str", "tool_params": {}}]}'
        ),
    )

    raw_tasks = planned.get("tasks", [])
    persisted_tasks: list[Task] = []

    for index, raw_task in enumerate(raw_tasks):
        if not isinstance(raw_task, dict):
            continue

        tool_name = raw_task.get("tool_name")
        if tool_name not in ALLOWED_TOOL_NAMES:
            raise ValueError(f"Unsupported planner tool_name: {tool_name}")

        task = Task(
            run_id=UUID(state["run_id"]),
            index=index,
            description=str(raw_task.get("description", "")),
            success_criteria=str(raw_task.get("success_criteria", "")),
            tool_name=tool_name,
            tool_params=raw_task.get("tool_params", {}) or {},
            status="pending",
        )
        db.add(task)
        persisted_tasks.append(task)

    await db.commit()

    for task in persisted_tasks:
        await db.refresh(task)

    return {
        **state,
        "tasks": [_serialize_task(task) for task in persisted_tasks],
        "current_task_index": -1,
        "current_task": None,
        "action_claim": None,
        "verification_result": None,
        "retry_count": 0,
        "error": None,
    }
