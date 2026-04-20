from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.schemas.verification import VerificationResult

VerifierFn = Callable[[dict[str, Any]], Awaitable[VerificationResult]]

_RECOVERABLE_VERIFIER_MARKERS = (
    "timeout",
    "timed out",
    "deadline exceeded",
    "rate limit",
    "too many requests",
    "429",
    "temporarily unavailable",
    "temporarily overloaded",
    "service unavailable",
    "connection reset",
    "connection refused",
    "broken pipe",
    "cancel scope",
    "session is not initialized",
    "stdio",
)

_UNRECOVERABLE_VERIFIER_MARKERS = (
    "permission denied",
    "outside allowed paths",
    "unsupported",
    "invalid selector",
    "missing required",
    "must not be empty",
)


class DeterministicVerifierError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        category: str,
        retryable: bool,
        tool_name: str,
        exception_type: str | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.retryable = retryable
        self.tool_name = tool_name
        self.exception_type = exception_type or self.__class__.__name__

    def to_error_details(self, *, source: str) -> dict[str, Any]:
        return {
            "message": str(self),
            "category": self.category,
            "retryable": self.retryable,
            "tool_name": self.tool_name,
            "source": source,
            "exception_type": self.exception_type,
        }


def coerce_verifier_exception(exc: Exception, *, tool_name: str) -> DeterministicVerifierError:
    if isinstance(exc, DeterministicVerifierError):
        return exc

    if hasattr(exc, "to_error_details"):
        details = exc.to_error_details(source="deterministic_verifier")
        if isinstance(details, dict):
            message = details.get("message")
            return DeterministicVerifierError(
                message.strip() if isinstance(message, str) and message.strip() else str(exc),
                category=str(details.get("category") or "verification_error"),
                retryable=bool(details.get("retryable")),
                tool_name=str(details.get("tool_name") or tool_name),
                exception_type=str(details.get("exception_type") or exc.__class__.__name__),
            )

    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()

    if isinstance(exc, TimeoutError) or any(marker in lowered for marker in _RECOVERABLE_VERIFIER_MARKERS):
        return DeterministicVerifierError(
            message,
            category="timeout" if "timeout" in lowered or "timed out" in lowered else "verifier_unavailable",
            retryable=True,
            tool_name=tool_name,
            exception_type=exc.__class__.__name__,
        )

    if any(marker in lowered for marker in _UNRECOVERABLE_VERIFIER_MARKERS):
        return DeterministicVerifierError(
            message,
            category="verification_error",
            retryable=False,
            tool_name=tool_name,
            exception_type=exc.__class__.__name__,
        )

    return DeterministicVerifierError(
        message,
        category="verification_error",
        retryable=False,
        tool_name=tool_name,
        exception_type=exc.__class__.__name__,
    )


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
                outcome="inconclusive",
                summary="No deterministic verifier exists for this tool.",
                ambiguity_reason="No verifier was registered for the claimed tool.",
                failure_indicators=["No deterministic verifier registered."],
            )

        try:
            result = await verifier(action_claim)
        except Exception as exc:
            raise coerce_verifier_exception(exc, tool_name=str(tool_name or "unknown.tool")) from exc
        if result.method != "deterministic":
            return result.model_copy(update={"method": "deterministic"})
        return result

    def needs_judge(self, result: VerificationResult) -> bool:
        error_details = result.error_details or {}
        if error_details.get("source") == "deterministic_verifier":
            return False
        return (
            not result.verified
            and result.outcome in {"evidence_missing", "inconclusive"}
            and result.confidence < 0.75
        )


registry = VerificationRegistry()
