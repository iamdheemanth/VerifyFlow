from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.domain import (
    Escalation,
    Run,
    RunTelemetry,
    Task,
    TaskAttempt,
    ReviewerDecision,
    LedgerEntry,
    utcnow,
)
from app.registry.base import coerce_verifier_exception

_UNRECOVERABLE_FAILURE_MARKERS = (
    "unsupported tool",
    "unsupported tool_name",
    "unsupported browser tool",
    "unsupported filesystem tool",
    "unsupported github tool",
    "no current task selected",
    "no current task available",
    "no current task or action claim",
    "no browser selector candidates",
    "element not found",
    "selector not found",
    "invalid selector",
    "missing required",
    "outside allowed paths",
    "permission denied",
)

_RECOVERABLE_FAILURE_MARKERS = (
    "timeout",
    "temporarily unavailable",
    "temporarily overloaded",
    "rate limit",
    "429",
    "connection reset",
    "connection aborted",
    "connection refused",
)


def build_error_details(
    message: str | None,
    *,
    source: str,
    category: str | None = None,
    retryable: bool | None = None,
    status_code: int | None = None,
    raw_output: str | None = None,
) -> dict[str, Any]:
    normalized_message = (message or "").strip() or "Unknown error"
    details: dict[str, Any] = {
        "message": normalized_message,
        "source": source,
    }
    if category is not None:
        details["category"] = category
    if retryable is not None:
        details["retryable"] = retryable
    if status_code is not None:
        details["status_code"] = status_code
    if raw_output:
        details["raw_output"] = raw_output[:500]
    return details


def _trim_text(value: str, *, limit: int = 500) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def _sanitize_failure_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 3:
        return "<truncated>"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _trim_text(value)
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in list(value.items())[:20]:
            if key in {"raw_output", "prompt_template"}:
                continue
            sanitized[str(key)] = _sanitize_failure_value(item, depth=depth + 1)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_failure_value(item, depth=depth + 1) for item in value[:20]]
    return _trim_text(repr(value))


def build_catastrophic_failure_record(
    *,
    state: dict[str, Any] | None,
    exc: Exception,
) -> dict[str, Any]:
    current_task = state.get("current_task") if isinstance(state, dict) else None
    verification_result = state.get("verification_result") if isinstance(state, dict) else None
    action_claim = state.get("action_claim") if isinstance(state, dict) else None

    return {
        "category": "catastrophic_orchestration_failure",
        "message": _trim_text(str(exc) or exc.__class__.__name__),
        "exception_type": exc.__class__.__name__,
        "decision": state.get("decision") if isinstance(state, dict) else None,
        "current_attempt_id": state.get("current_attempt_id") if isinstance(state, dict) else None,
        "current_task": _sanitize_failure_value(current_task),
        "action_claim": _sanitize_failure_value(action_claim),
        "verification_result": _sanitize_failure_value(verification_result),
        "recorded_at": utcnow().isoformat(),
    }


def _sum_llm_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    llm_events = [event for event in events if event.get("type") == "llm_call"]
    return {
        "prompt_tokens": sum(int(event.get("prompt_tokens", 0) or 0) for event in llm_events),
        "completion_tokens": sum(int(event.get("completion_tokens", 0) or 0) for event in llm_events),
        "total_tokens": sum(int(event.get("total_tokens", 0) or 0) for event in llm_events),
        "estimated_cost_usd": sum(float(event.get("estimated_cost_usd", 0.0) or 0.0) for event in llm_events),
        "llm_events": llm_events,
    }


def classify_retryability(
    *,
    action_claim: dict[str, Any] | None,
    verification_result: dict[str, Any] | None,
) -> dict[str, Any]:
    details_candidates: list[dict[str, Any]] = []
    if isinstance(action_claim, dict):
        details = action_claim.get("error_details")
        if isinstance(details, dict):
            details_candidates.append(details)
    if isinstance(verification_result, dict):
        details = verification_result.get("error_details")
        if isinstance(details, dict):
            details_candidates.append(details)

    for details in details_candidates:
        retryable = details.get("retryable")
        category = details.get("category")
        reason = details.get("message")
        if isinstance(retryable, bool):
            return {
                "retryable": retryable,
                "category": category or ("recoverable" if retryable else "unrecoverable"),
                "reason": reason if isinstance(reason, str) and reason.strip() else None,
            }

    if not action_claim and not verification_result:
        return {"retryable": True, "category": "unknown", "reason": None}

    fragments: list[str] = []
    if isinstance(action_claim, dict):
        error = action_claim.get("error")
        if isinstance(error, str) and error.strip():
            fragments.append(error.strip())

    if isinstance(verification_result, dict):
        for key in ("evidence", "judge_reasoning"):
            value = verification_result.get(key)
            if isinstance(value, str) and value.strip():
                fragments.append(value.strip())
        indicators = verification_result.get("failure_indicators")
        if isinstance(indicators, list):
            for indicator in indicators:
                if isinstance(indicator, str) and indicator.strip():
                    fragments.append(indicator.strip())

    failure_text = " | ".join(fragments).lower()
    if not failure_text:
        return {"retryable": True, "category": "unknown", "reason": None}

    if any(marker in failure_text for marker in _RECOVERABLE_FAILURE_MARKERS):
        return {"retryable": True, "category": "transient", "reason": None}

    if any(marker in failure_text for marker in _UNRECOVERABLE_FAILURE_MARKERS):
        return {
            "retryable": False,
            "category": "unrecoverable",
            "reason": fragments[0] if fragments else "Encountered an unrecoverable execution failure.",
        }

    return {"retryable": True, "category": "recoverable", "reason": None}


def build_verifier_failure_payload(exc: Exception, *, tool_name: str | None = None) -> dict[str, Any]:
    verifier_error = coerce_verifier_exception(exc, tool_name=tool_name or "unknown.tool")
    error_details = verifier_error.to_error_details(source="deterministic_verifier")
    retryable = bool(error_details.get("retryable"))
    summary = str(verifier_error)

    if retryable:
        evidence = "Deterministic verification could not complete because the verifier-side dependency failed transiently."
        ambiguity_reason = (
            "The verifier failed before it could confirm or disprove the executor claim, so a bounded retry is allowed."
        )
    else:
        evidence = "Deterministic verification failed in a non-retryable way before the claim could be checked."
        ambiguity_reason = (
            "The verifier itself could not complete in a stable way, so the claim remains unproven and should not be retried indefinitely."
        )

    return {
        "verified": False,
        "confidence": 0.0,
        "method": "deterministic",
        "evidence": evidence,
        "judge_reasoning": None,
        "outcome": "inconclusive",
        "summary": summary,
        "observed_evidence": [summary],
        "failure_indicators": [summary],
        "ambiguity_reason": ambiguity_reason,
        "error_details": error_details,
    }


async def create_ledger_entry(
    db: AsyncSession,
    *,
    run_id: str,
    task_id: str,
    result: dict[str, Any],
    attempt_id: str | None = None,
) -> bool:
    from app.models.domain import LedgerEntry

    existing_query = select(LedgerEntry).where(
        LedgerEntry.task_id == UUID(task_id),
        LedgerEntry.run_id == UUID(run_id),
        LedgerEntry.verification_method == result["method"],
        LedgerEntry.confidence == result["confidence"],
        LedgerEntry.verified == result["verified"],
        LedgerEntry.evidence == result["evidence"],
        LedgerEntry.judge_reasoning == result.get("judge_reasoning"),
    )
    if attempt_id:
        existing_query = existing_query.where(LedgerEntry.attempt_id == UUID(attempt_id))
    else:
        existing_query = existing_query.where(LedgerEntry.attempt_id.is_(None))

    existing = (await db.execute(existing_query)).scalar_one_or_none()
    if existing is not None:
        return False

    entry = LedgerEntry(
        task_id=UUID(task_id),
        run_id=UUID(run_id),
        attempt_id=UUID(attempt_id) if attempt_id else None,
        verification_method=result["method"],
        confidence=result["confidence"],
        verified=result["verified"],
        evidence=result["evidence"],
        judge_reasoning=result.get("judge_reasoning"),
    )
    db.add(entry)
    await db.commit()
    return True


async def persist_catastrophic_failure(
    db: AsyncSession,
    *,
    run_id: str,
    state: dict[str, Any] | None,
    exc: Exception,
) -> dict[str, Any]:
    run_uuid = UUID(run_id)
    run_result = await db.execute(
        select(Run)
        .options(
            selectinload(Run.tasks),
            selectinload(Run.escalations),
        )
        .where(Run.id == run_uuid)
    )
    run = run_result.scalar_one_or_none()
    if run is None:
        return build_catastrophic_failure_record(state=state, exc=exc)

    failure_record = build_catastrophic_failure_record(state=state, exc=exc)
    run.status = "failed"
    run.failure_record = failure_record
    run.updated_at = utcnow()

    current_task_data = state.get("current_task") if isinstance(state, dict) else None
    task = None
    if isinstance(current_task_data, dict):
        task_id = current_task_data.get("id")
        if isinstance(task_id, str):
            task_result = await db.execute(select(Task).where(Task.id == UUID(task_id)))
            task = task_result.scalar_one_or_none()

    attempt: TaskAttempt | None = None
    current_attempt_id = state.get("current_attempt_id") if isinstance(state, dict) else None
    if isinstance(current_attempt_id, str):
        attempt_result = await db.execute(select(TaskAttempt).where(TaskAttempt.id == UUID(current_attempt_id)))
        attempt = attempt_result.scalar_one_or_none()

    if task is not None:
        if task.status != "verified":
            task.status = "escalated"
        task.claimed_result = {
            "claimed_success": False,
            "error": failure_record["message"],
            "error_details": {
                "category": failure_record["category"],
                "source": "orchestrator.graph",
                "retryable": False,
                "message": failure_record["message"],
                "exception_type": failure_record["exception_type"],
            },
            "catastrophic_failure": failure_record,
        }

        if attempt is None:
            attempt = TaskAttempt(
                run_id=run_uuid,
                task_id=task.id,
                attempt_index=task.retry_count,
                tool_name=task.tool_name,
                tool_params=task.tool_params,
                execution_steps=[],
                tool_calls=[],
            )
            db.add(attempt)
            await db.flush()

        attempt.action_claim = state.get("action_claim") if isinstance(state, dict) else None
        attempt.verification_payload = {
            "verified": False,
            "confidence": 0.0,
            "method": "hybrid",
            "outcome": "catastrophic_failure",
            "summary": "The orchestration graph crashed before the task could be resolved normally.",
            "evidence": failure_record["message"],
            "failure_indicators": [failure_record["message"]],
            "error_details": {
                "category": failure_record["category"],
                "source": "orchestrator.graph",
                "retryable": False,
                "message": failure_record["message"],
                "exception_type": failure_record["exception_type"],
            },
        }
        attempt.claimed_success = False
        attempt.verification_method = "hybrid"
        attempt.final_confidence = 0.0
        attempt.outcome = "escalated"
        attempt.error = failure_record["message"]
        attempt.execution_steps = [
            *(attempt.execution_steps or []),
            {
                "type": "catastrophic_failure",
                "failure_record": failure_record,
                "recorded_at": utcnow().isoformat(),
            },
        ]

        existing_escalation = next(
            (item for item in run.escalations if item.task_id == task.id and item.status == "pending_review"),
            None,
        )
        if existing_escalation is None:
            escalation = Escalation(
                run_id=run_uuid,
                task_id=task.id,
                status="pending_review",
                failure_reason=failure_record["message"],
                evidence_bundle=failure_record,
            )
            db.add(escalation)

        await db.flush()
        await create_ledger_entry(
            db,
            run_id=run_id,
            task_id=str(task.id),
            result={
                "verified": False,
                "confidence": 0.0,
                "method": "hybrid",
                "evidence": f"Catastrophic orchestration failure: {failure_record['message']}",
                "judge_reasoning": None,
            },
            attempt_id=str(attempt.id) if attempt is not None else None,
        )

    await db.commit()
    await refresh_run_telemetry(db, run_id)
    return failure_record


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
    error_details = action_claim.get("error_details")
    if isinstance(error_details, dict):
        message = error_details.get("message")
        if isinstance(message, str) and message.strip():
            attempt.error = message.strip()
        else:
            attempt.error = action_claim.get("error")
    else:
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
    verification_error = verification_payload.get("error_details")
    if isinstance(verification_error, dict):
        message = verification_error.get("message")
        if isinstance(message, str) and message.strip():
            attempt.error = message.strip()
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


async def set_attempt_outcome(
    db: AsyncSession,
    *,
    attempt_id: str | None,
    outcome: str,
) -> TaskAttempt | None:
    if attempt_id is None:
        return None

    result = await db.execute(select(TaskAttempt).where(TaskAttempt.id == UUID(attempt_id)))
    attempt = result.scalar_one_or_none()
    if attempt is None:
        return None

    attempt.outcome = outcome
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


async def _load_run(db: AsyncSession, run_id: UUID) -> Run:
    result = await db.execute(select(Run).where(Run.id == run_id))
    return result.scalar_one()


async def _load_task(db: AsyncSession, task_id: UUID) -> Task:
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one()


async def _reconcile_run_status_after_review(db: AsyncSession, run: Run) -> Run:
    task_result = await db.execute(select(Task).where(Task.run_id == run.id).order_by(Task.index.asc()))
    tasks = task_result.scalars().all()
    task_statuses = {task.status for task in tasks}

    if tasks and task_statuses == {"verified"}:
        run.status = "completed"
    elif "pending" in task_statuses:
        run.status = "pending"
    elif "executing" in task_statuses or "claimed" in task_statuses:
        run.status = "executing"
    elif "escalated" in task_statuses:
        run.status = "needs_review"
    elif "failed" in task_statuses:
        run.status = "failed"
    else:
        run.status = "pending"
    run.updated_at = utcnow()
    return run


async def record_reviewer_decision(
    db: AsyncSession,
    *,
    escalation: Escalation,
    decision: str,
    notes: str | None,
    reviewer_key: str,
    reviewer_display_name: str | None,
) -> ReviewerDecision:
    if not reviewer_key.strip():
        raise ValueError("Reviewer key must not be empty.")
    if escalation.status != "pending_review" or escalation.resolved_at is not None:
        raise ValueError("Escalation has already been resolved and cannot accept another decision.")

    task = await _load_task(db, escalation.task_id)
    run = await _load_run(db, escalation.run_id)

    escalation.status = {
        "approve": "approved",
        "reject": "rejected",
        "send_back": "sent_back",
    }[decision]
    escalation.resolved_at = utcnow()

    if decision == "approve":
        task.status = "verified"
    elif decision == "reject":
        task.status = "failed"
    elif decision == "send_back":
        task.status = "pending"
        task.retry_count = 0
        task.claimed_result = None

    await _reconcile_run_status_after_review(db, run)

    reviewer_name = (reviewer_display_name or reviewer_key).strip()
    reviewer_decision = ReviewerDecision(
        escalation_id=escalation.id,
        run_id=escalation.run_id,
        task_id=escalation.task_id,
        reviewer_key=reviewer_key.strip(),
        reviewer_display_name=reviewer_display_name.strip() if isinstance(reviewer_display_name, str) and reviewer_display_name.strip() else None,
        reviewer_name=reviewer_name,
        decision=decision,
        notes=notes,
    )
    db.add(reviewer_decision)
    await db.commit()
    await db.refresh(reviewer_decision)
    return reviewer_decision
