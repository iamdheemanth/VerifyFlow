from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import LedgerEntry, Task
from app.orchestrator.states import VerifyFlowState
from app.schemas.verification import VerificationResult


async def _load_task(db: AsyncSession, task_id: str) -> Task:
    result = await db.execute(select(Task).where(Task.id == UUID(task_id)))
    return result.scalar_one()


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
                f"{json.dumps(state['action_claim'], indent=2)}\n"
                "     \n"
                "DETERMINISTIC CHECK RESULT:\n"
                f"{json.dumps(state['verification_result'], indent=2)}\n"
                "     \n"
                "Now find evidence this task was NOT done correctly."
            ),
        },
    ]

    raw_response = await judge_llm.chat(
        messages=messages,
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    response = json.loads(judge_llm._strip_markdown_fences(raw_response))

    judge_result = VerificationResult(
        verified=bool(response["verified"]),
        confidence=float(response["confidence"]),
        method="llm_judge",
        evidence=str(response["evidence"]),
        judge_reasoning=str(response["reasoning"]),
    )

    verification_payload: dict[str, Any] = judge_result.model_dump()
    verification_payload["failure_indicators"] = response.get("failure_indicators", [])

    task = await _load_task(db, current_task["id"])
    ledger_entry = LedgerEntry(
        task_id=task.id,
        run_id=task.run_id,
        verification_method="llm_judge",
        confidence=judge_result.confidence,
        verified=judge_result.verified,
        evidence=judge_result.evidence,
        judge_reasoning=judge_result.judge_reasoning,
    )
    db.add(ledger_entry)
    await db.commit()

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
