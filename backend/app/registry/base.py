from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.schemas.verification import VerificationResult

VerifierFn = Callable[[dict[str, Any]], Awaitable[VerificationResult]]


class VerificationRegistry:
    def __init__(self):
        self._verifiers: dict[str, VerifierFn] = {}

    def register(self, tool_name: str):
        def decorator(func: VerifierFn) -> VerifierFn:
            self._verifiers[tool_name] = func
            return func

        return decorator

    async def verify(self, action_claim: dict) -> VerificationResult:
        tool_name = action_claim.get("tool_name")
        verifier = self._verifiers.get(tool_name)
        if verifier is None:
            return VerificationResult(
                verified=False,
                confidence=0.0,
                method="deterministic",
                evidence=(
                    "No deterministic verifier registered for this tool. "
                    "Routing to LLM judge."
                ),
            )

        result = await verifier(action_claim)
        if result.method != "deterministic":
            return result.model_copy(update={"method": "deterministic"})
        return result

    def needs_judge(self, result: VerificationResult) -> bool:
        return result.confidence == 0.0 and not result.verified


registry = VerificationRegistry()
