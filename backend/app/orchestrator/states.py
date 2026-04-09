from __future__ import annotations

from typing import TypedDict


class VerifyFlowState(TypedDict):
    run_id: str
    goal: str
    acceptance_criteria: str | None
    tasks: list[dict]
    current_task_index: int
    current_task: dict | None
    action_claim: dict | None
    verification_result: dict | None
    retry_count: int
    error: str | None
