from __future__ import annotations

from app.registry.base import registry
from app.schemas.verification import VerificationResult


def _claimed_success(action_claim: dict) -> bool:
    result = action_claim.get("result")
    if isinstance(result, dict):
        if result.get("is_error") is True:
            return False
        structured = result.get("structured_content")
        if isinstance(structured, dict):
            for key in ("success", "ok", "clicked", "filled"):
                value = structured.get(key)
                if isinstance(value, bool):
                    return value
    return bool(action_claim.get("claimed_success"))


@registry.register("browser.navigate")
async def verify_browser_navigate(action_claim: dict) -> VerificationResult:
    success = _claimed_success(action_claim)
    return VerificationResult(
        verified=success,
        confidence=0.7,
        method="deterministic",
        evidence="Navigation claimed successful. Routing to judge for content verification.",
    )


@registry.register("browser.fill")
async def verify_browser_fill(action_claim: dict) -> VerificationResult:
    success = _claimed_success(action_claim)
    return VerificationResult(
        verified=success,
        confidence=0.6,
        method="deterministic",
        evidence="Browser fill action claimed successful. Routing to judge.",
    )


@registry.register("browser.click")
async def verify_browser_click(action_claim: dict) -> VerificationResult:
    success = _claimed_success(action_claim)
    return VerificationResult(
        verified=success,
        confidence=0.6,
        method="deterministic",
        evidence="Browser click action claimed successful. Routing to judge.",
    )
