from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import LLMClientError
from app.models.domain import Task
from app.orchestrator.states import VerifyFlowState
from app.schemas.verification import VerificationResult
from app.services import reliability


async def _load_task(db: AsyncSession, task_id: str) -> Task:
    result = await db.execute(select(Task).where(Task.id == UUID(task_id)))
    return result.scalar_one()


def _format_verification_context(verification_result: dict[str, Any] | None) -> str:
    if not isinstance(verification_result, dict):
        return "No deterministic verification result was available."

    lines = [
        f"Outcome: {verification_result.get('outcome')}",
        f"Verified: {verification_result.get('verified')}",
        f"Confidence: {verification_result.get('confidence')}",
        f"Evidence summary: {verification_result.get('evidence')}",
    ]

    summary = verification_result.get("summary")
    if isinstance(summary, str) and summary.strip():
        lines.append(f"Summary: {summary.strip()}")

    for label, key in (
        ("Expected evidence", "expected_evidence"),
        ("Observed evidence", "observed_evidence"),
        ("Missing evidence", "missing_evidence"),
        ("Failure indicators", "failure_indicators"),
    ):
        values = verification_result.get(key)
        if isinstance(values, list) and values:
            lines.append(f"{label}:")
            lines.extend(f"- {value}" for value in values if isinstance(value, str) and value.strip())

    ambiguity_reason = verification_result.get("ambiguity_reason")
    if isinstance(ambiguity_reason, str) and ambiguity_reason.strip():
        lines.append(f"Ambiguity reason: {ambiguity_reason.strip()}")

    error_details = verification_result.get("error_details")
    if isinstance(error_details, dict):
        message = error_details.get("message")
        category = error_details.get("category")
        if isinstance(message, str) and message.strip():
            lines.append(f"Verifier error: {message.strip()}")
        if isinstance(category, str) and category.strip():
            lines.append(f"Verifier error category: {category.strip()}")

    return "\n".join(lines)


async def evaluate(state: VerifyFlowState, db: AsyncSession) -> VerifyFlowState:
    from app.core.llm import judge_llm

    current_task = state["current_task"]
    if current_task is None:
        return {**state, "error": "No current task available for judging."}

    messages = [
        {
            "role": "system",
            "content": (
                "You are an adversarial verification agent. Your job is to find \n"
                "evidence that a task was NOT completed correctly. \n"
                "You are NOT trying to confirm success — you are actively looking \n"
                "for signs of failure, partial completion, hallucination, or \n"
                "incorrect execution. Be skeptical. Be specific.\n"
                "     \n"
                "Return JSON with this exact shape:\n"
                "{\n"
                '  "verified": bool,\n'
                '  "confidence": float between 0.0 and 1.0,\n'
                '  "evidence": "one sentence describing what you found",\n'
                '  "failure_indicators": ["list of specific things that look wrong or incomplete"],\n'
                '  "reasoning": "your step-by-step analysis"\n'
                "}\n"
                "     \n"
                "Confidence guide:\n"
                "  0.9–1.0: Strong evidence the task IS correctly completed\n"
                "  0.7–0.89: Likely completed but minor uncertainties remain\n"
                "  0.5–0.69: Ambiguous — could go either way\n"
                "  0.3–0.49: Likely NOT completed or done incorrectly\n"
                "  0.0–0.29: Strong evidence of failure or hallucination"
            ),
        },
        {
            "role": "user",
            "content": (
                f"TASK DESCRIPTION: {current_task['description']}\n"
                "     \n"
                f"SUCCESS CRITERIA: {current_task['success_criteria']}\n"
                "     \n"
                "WHAT THE AGENT CLAIMED IT DID:\n"
                f"{state['action_claim']}\n"
                "     \n"
                "DETERMINISTIC CHECK RESULT:\n"
                f"{_format_verification_context(state['verification_result'])}\n"
                "     \n"
                "Your goal is to find evidence this task was NOT done correctly. "
                "Pay special attention to missing evidence, contradictions between the claim and the page/system state, "
                "and any ambiguity called out by the deterministic verifier."
            ),
        },
    ]

    try:
        response = await judge_llm.chat_json(
            messages=messages,
            schema_hint=(
                '{"verified": true, "confidence": 0.0, "evidence": "string", '
                '"failure_indicators": ["string"], "reasoning": "string"}'
            ),
            temperature=0.1,
        )
        judge_result = VerificationResult(
            verified=bool(response["verified"]),
            confidence=float(response["confidence"]),
            method="llm_judge",
            evidence=str(response["evidence"]),
            judge_reasoning=str(response["reasoning"]),
            outcome="verified" if bool(response["verified"]) else "inconclusive",
            summary=str(response["evidence"]),
        )

        verification_payload: dict[str, Any] = judge_result.model_dump()
        verification_payload["failure_indicators"] = response.get("failure_indicators", [])
    except Exception as exc:
        if isinstance(exc, LLMClientError):
            error_details = exc.to_error_details(source="judge")
        else:
            error_details = reliability.build_error_details(
                str(exc),
                source="judge",
                category="verification_error",
                retryable=False,
            )
        verification_payload = {
            "verified": False,
            "confidence": 0.0,
            "method": "llm_judge",
            "evidence": "Judge failed to produce usable verification output.",
            "judge_reasoning": error_details["message"],
            "failure_indicators": [error_details["message"]],
            "error_details": error_details,
        }

    task = await _load_task(db, current_task["id"])
    await reliability.create_ledger_entry(
        db,
        run_id=str(task.run_id),
        task_id=str(task.id),
        result={
            "method": "llm_judge",
            "confidence": verification_payload["confidence"],
            "verified": verification_payload["verified"],
            "evidence": verification_payload["evidence"],
            "judge_reasoning": verification_payload.get("judge_reasoning"),
        },
        attempt_id=state.get("current_attempt_id"),
    )

    updated_task = {
        **current_task,
        "status": task.status,
    }

    return {
        **state,
        "current_task": updated_task,
        "verification_result": verification_payload,
        "error": None,
    }
