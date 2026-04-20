from __future__ import annotations

from typing import TypedDict


class VerifyFlowState(TypedDict):
    run_id: str
    goal: str
    acceptance_criteria: str | None
    tasks: list[dict]
    current_task_index: int
    current_task: dict | None
    current_attempt_id: str | None
    action_claim: dict | None
    verification_result: dict | None
    executor_telemetry: list[dict]
    verifier_telemetry: list[dict]
    retry_count: int
    decision: str | None
    retryable: bool
    escalation_reason: str | None
    error: str | None
