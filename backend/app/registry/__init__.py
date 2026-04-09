from __future__ import annotations

from app.orchestrator.states import VerifyFlowState


async def verify(state: VerifyFlowState) -> dict:
    current_task = state["current_task"] or {}
    tool_name = current_task.get("tool_name")

    if tool_name == "ambiguous.stub":
        return {
            "verified": False,
            "confidence": 0.5,
            "method": "llm_judge",
            "evidence": "Deterministic verification was inconclusive.",
            "judge_reasoning": None,
        }

    return {
        "verified": True,
        "confidence": 1.0,
        "method": "deterministic",
        "evidence": "Stub verification passed.",
        "judge_reasoning": None,
    }
