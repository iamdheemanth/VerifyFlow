from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import (
    Escalation,
    Run,
    RunTelemetry,
    Task,
    TaskAttempt,
    ReviewerDecision,
    utcnow,
)


def _sum_llm_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    llm_events = [event for event in events if event.get("type") == "llm_call"]
    return {
        "prompt_tokens": sum(int(event.get("prompt_tokens", 0) or 0) for event in llm_events),
        "completion_tokens": sum(int(event.get("completion_tokens", 0) or 0) for event in llm_events),
        "total_tokens": sum(int(event.get("total_tokens", 0) or 0) for event in llm_events),
        "estimated_cost_usd": sum(float(event.get("estimated_cost_usd", 0.0) or 0.0) for event in llm_events),
        "llm_events": llm_events,
    }


async def start_task_attempt(
    db: AsyncSession,
    *,
    run_id: str,
    task: Task,
    tool_params: dict[str, Any],
) -> TaskAttempt:
    attempt = TaskAttempt(
        run_id=UUID(run_id),
        task_id=task.id,
        attempt_index=task.retry_count,
        tool_name=task.tool_name,
        tool_params=tool_params,
        execution_steps=[
            {
                "type": "planned",
                "description": task.description,
                "success_criteria": task.success_criteria,
                "tool_name": task.tool_name,
                "tool_params": tool_params,
                "recorded_at": utcnow().isoformat(),
            }
        ],
        tool_calls=[],
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    return attempt


async def finalize_executor_attempt(
    db: AsyncSession,
    *,
    attempt_id: str | None,
    action_claim: dict[str, Any],
    executor_latency_ms: float,
    telemetry_events: list[dict[str, Any]],
) -> TaskAttempt | None:
    if attempt_id is None:
        return None

    result = await db.execute(select(TaskAttempt).where(TaskAttempt.id == UUID(attempt_id)))
    attempt = result.scalar_one_or_none()
    if attempt is None:
        return None

    llm_totals = _sum_llm_events(telemetry_events)
    attempt.action_claim = action_claim
    attempt.claimed_success = bool(action_claim.get("claimed_success"))
    attempt.executor_latency_ms = executor_latency_ms
    attempt.tool_calls = [
        {
            "tool_name": action_claim.get("tool_name"),
            "params": action_claim.get("params"),
            "claimed_success": action_claim.get("claimed_success"),
        }
    ]
    attempt.token_input = llm_totals["prompt_tokens"]
    attempt.token_output = llm_totals["completion_tokens"]
    attempt.token_total = llm_totals["total_tokens"]
    attempt.estimated_cost_usd = llm_totals["estimated_cost_usd"]
    attempt.error = action_claim.get("error")
    attempt.execution_steps = [
        *attempt.execution_steps,
        {
            "type": "claimed",
            "action_claim": action_claim,
            "executor_latency_ms": executor_latency_ms,
            "telemetry_events": telemetry_events,
            "recorded_at": utcnow().isoformat(),
        },
    ]
    await db.commit()
    await db.refresh(attempt)
    return attempt


async def finalize_verification_attempt(
    db: AsyncSession,
    *,
    attempt_id: str | None,
    verification_payload: dict[str, Any],
    verifier_latency_ms: float,
    telemetry_events: list[dict[str, Any]],
    outcome: str,
) -> TaskAttempt | None:
    if attempt_id is None:
        return None

    result = await db.execute(select(TaskAttempt).where(TaskAttempt.id == UUID(attempt_id)))
    attempt = result.scalar_one_or_none()
    if attempt is None:
        return None

    llm_totals = _sum_llm_events(telemetry_events)
    attempt.verification_payload = verification_payload
    attempt.verification_method = verification_payload.get("method")
    attempt.final_confidence = verification_payload.get("confidence")
    attempt.verifier_latency_ms = verifier_latency_ms
    attempt.total_latency_ms = (attempt.executor_latency_ms or 0.0) + verifier_latency_ms
    attempt.token_input += llm_totals["prompt_tokens"]
    attempt.token_output += llm_totals["completion_tokens"]
    attempt.token_total += llm_totals["total_tokens"]
    attempt.estimated_cost_usd += llm_totals["estimated_cost_usd"]
    attempt.outcome = outcome
    attempt.execution_steps = [
        *attempt.execution_steps,
        {
            "type": "verified",
            "verification_payload": verification_payload,
            "verifier_latency_ms": verifier_latency_ms,
            "telemetry_events": telemetry_events,
            "outcome": outcome,
            "recorded_at": utcnow().isoformat(),
        },
    ]
    await db.commit()
    await db.refresh(attempt)
    return attempt


async def refresh_run_telemetry(db: AsyncSession, run_id: str) -> RunTelemetry:
    run_uuid = UUID(run_id)
    run_result = await db.execute(select(Run).where(Run.id == run_uuid))
    run = run_result.scalar_one()

    attempts_result = await db.execute(select(TaskAttempt).where(TaskAttempt.run_id == run_uuid))
    attempts = attempts_result.scalars().all()

    telemetry_result = await db.execute(select(RunTelemetry).where(RunTelemetry.run_id == run_uuid))
    telemetry = telemetry_result.scalar_one_or_none()
    if telemetry is None:
        telemetry = RunTelemetry(run_id=run_uuid)
        db.add(telemetry)

    telemetry.total_executor_latency_ms = sum(float(item.executor_latency_ms or 0.0) for item in attempts)
    telemetry.total_verifier_latency_ms = sum(float(item.verifier_latency_ms or 0.0) for item in attempts)
    telemetry.total_task_latency_ms = sum(float(item.total_latency_ms or 0.0) for item in attempts)
    telemetry.total_retry_count = sum(1 for item in attempts if item.attempt_index > 0)
    telemetry.total_token_input = sum(int(item.token_input or 0) for item in attempts)
    telemetry.total_token_output = sum(int(item.token_output or 0) for item in attempts)
    telemetry.total_token_total = sum(int(item.token_total or 0) for item in attempts)
    telemetry.total_estimated_cost_usd = sum(float(item.estimated_cost_usd or 0.0) for item in attempts)
    telemetry.total_tool_calls = sum(len(item.tool_calls or []) for item in attempts)
    telemetry.deterministic_verifications = sum(1 for item in attempts if item.verification_method == "deterministic")
    telemetry.llm_judge_verifications = sum(1 for item in attempts if item.verification_method == "llm_judge")
    telemetry.hybrid_verifications = sum(1 for item in attempts if item.verification_method == "hybrid")
    confidences = [float(item.final_confidence) for item in attempts if item.final_confidence is not None]
    telemetry.average_confidence = (sum(confidences) / len(confidences)) if confidences else 0.0

    if confidences:
        run.latest_confidence = confidences[-1]

    await db.commit()
    await db.refresh(telemetry)
    return telemetry


async def create_escalation(
    db: AsyncSession,
    *,
    run_id: str,
    task_id: str,
    failure_reason: str,
    evidence_bundle: dict[str, Any],
) -> Escalation:
    escalation = Escalation(
        run_id=UUID(run_id),
        task_id=UUID(task_id),
        failure_reason=failure_reason,
        evidence_bundle=evidence_bundle,
    )
    db.add(escalation)
    await db.commit()
    await db.refresh(escalation)
    return escalation


async def record_reviewer_decision(
    db: AsyncSession,
    *,
    escalation: Escalation,
    decision: str,
    notes: str | None,
    reviewer_name: str | None,
) -> ReviewerDecision:
    escalation.status = {
        "approve": "approved",
        "reject": "rejected",
        "send_back": "sent_back",
    }[decision]
    escalation.resolved_at = utcnow()
    reviewer_decision = ReviewerDecision(
        escalation_id=escalation.id,
        run_id=escalation.run_id,
        task_id=escalation.task_id,
        reviewer_name=reviewer_name,
        decision=decision,
        notes=notes,
    )
    db.add(reviewer_decision)
    await db.commit()
    await db.refresh(reviewer_decision)
    return reviewer_decision
