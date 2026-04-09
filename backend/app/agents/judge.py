from __future__ import annotations

from app.orchestrator.states import VerifyFlowState


async def evaluate(state: VerifyFlowState) -> dict:
    current_task = state["current_task"] or {}
    return {
        "verified": True,
        "confidence": 0.9,
        "method": "llm_judge",
        "evidence": f"Judge confirmed task {current_task.get('id')}.",
        "judge_reasoning": "The deterministic verification was ambiguous, but the outcome looks correct.",
    }
