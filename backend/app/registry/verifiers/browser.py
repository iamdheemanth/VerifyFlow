from __future__ import annotations

import json

from app.registry.base import registry
from app.schemas.verification import VerificationResult


def _claimed_success(action_claim: dict) -> bool:
    result = action_claim.get("result")
    if isinstance(result, dict):
        if result.get("is_error") is True:
            return False
        structured = result.get("structured_content")
        if isinstance(structured, dict):
            for key in ("success", "ok", "clicked", "filled", "matched_text"):
                value = structured.get(key)
                if isinstance(value, bool):
                    return value
    return bool(action_claim.get("claimed_success"))


def _result_text(action_claim: dict) -> str:
    result = action_claim.get("result")
    if not isinstance(result, dict):
        return ""

    collected: list[str] = []

    structured = result.get("structured_content")
    if structured is not None:
        try:
            collected.append(json.dumps(structured))
        except TypeError:
            collected.append(str(structured))

    content = result.get("content")
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    collected.append(text)

    return "\n".join(part for part in collected if part).strip()


@registry.register("browser.navigate")
async def verify_browser_navigate(action_claim: dict) -> VerificationResult:
    success = _claimed_success(action_claim)
    expected_text = action_claim.get("params", {}).get("expected_text")
    if success and isinstance(expected_text, str) and expected_text.strip():
        success = expected_text in _result_text(action_claim)
    return VerificationResult(
        verified=success,
        confidence=1.0 if success else 0.7,
        method="deterministic",
        evidence=(
            "Navigation succeeded and the expected text was found in browser output."
            if success
            else "Navigation claimed successful. Routing to judge for content verification."
        ),
    )


@registry.register("browser.fill")
async def verify_browser_fill(action_claim: dict) -> VerificationResult:
    success = _claimed_success(action_claim)
    return VerificationResult(
        verified=success,
        confidence=1.0 if success else 0.6,
        method="deterministic",
        evidence=(
            "Browser fill action succeeded."
            if success
            else "Browser fill action claimed successful. Routing to judge."
        ),
    )


@registry.register("browser.click")
async def verify_browser_click(action_claim: dict) -> VerificationResult:
    success = _claimed_success(action_claim)
    expected_text = action_claim.get("params", {}).get("expected_text")
    if success and isinstance(expected_text, str) and expected_text.strip():
        success = expected_text in _result_text(action_claim)
    return VerificationResult(
        verified=success,
        confidence=1.0 if success else 0.7,
        method="deterministic",
        evidence=(
            "Browser click succeeded and the expected text was found in browser output."
            if success
            else "Browser click action claimed successful. Routing to judge."
        ),
    )
