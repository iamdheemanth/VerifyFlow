from __future__ import annotations

import json
from typing import Any

from app.registry.base import registry
from app.schemas.verification import VerificationResult


def _structured_result(action_claim: dict[str, Any]) -> dict[str, Any]:
    result = action_claim.get("result")
    if isinstance(result, dict):
        structured = result.get("structured_content")
        if isinstance(structured, dict):
            return structured
    return {}


def _content_text(action_claim: dict[str, Any]) -> str:
    result = action_claim.get("result")
    if not isinstance(result, dict):
        return ""

    parts: list[str] = []
    structured = result.get("structured_content")
    if structured is not None:
        try:
            parts.append(json.dumps(structured))
        except TypeError:
            parts.append(str(structured))

    content = result.get("content")
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())

    return "\n".join(parts).strip()


def _combined_browser_text(action_claim: dict[str, Any]) -> str:
    structured = _structured_result(action_claim)
    candidates = [
        structured.get("page_title"),
        structured.get("page_text_excerpt"),
        _content_text(action_claim),
    ]
    return "\n".join(value for value in candidates if isinstance(value, str) and value.strip())


def _expected_text(action_claim: dict[str, Any]) -> str | None:
    params = action_claim.get("params", {})
    if not isinstance(params, dict):
        return None
    expected = params.get("expected_text")
    if isinstance(expected, str) and expected.strip():
        return expected.strip()
    return None


def _base_failure_details(action_claim: dict[str, Any]) -> dict[str, Any] | None:
    details = action_claim.get("error_details")
    return details if isinstance(details, dict) else None


def _tool_execution_failed(action_claim: dict[str, Any]) -> VerificationResult | None:
    details = _base_failure_details(action_claim)
    structured = _structured_result(action_claim)
    result = action_claim.get("result")
    claimed_success = bool(action_claim.get("claimed_success"))
    tool_name = str(action_claim.get("tool_name") or "browser")

    failure_message = None
    if isinstance(details, dict):
        message = details.get("message")
        if isinstance(message, str) and message.strip():
            failure_message = message.strip()
    if failure_message is None and isinstance(result, dict):
        error_message = result.get("error")
        if isinstance(error_message, str) and error_message.strip():
            failure_message = error_message.strip()
    if failure_message is None:
        error_message = action_claim.get("error")
        if isinstance(error_message, str) and error_message.strip():
            failure_message = error_message.strip()

    if result is None and not claimed_success and failure_message:
        return VerificationResult(
            verified=False,
            confidence=1.0,
            method="deterministic",
            evidence=f"{tool_name} execution failed before verification evidence could be collected.",
            outcome="execution_failed",
            summary=failure_message,
            observed_evidence=[failure_message],
            failure_indicators=[failure_message],
            error_details=details,
        )

    if isinstance(result, dict) and result.get("is_error") is True:
        return VerificationResult(
            verified=False,
            confidence=1.0,
            method="deterministic",
            evidence=f"{tool_name} returned an explicit tool error.",
            outcome="execution_failed",
            summary=failure_message or "Tool reported an error result.",
            observed_evidence=[failure_message] if failure_message else [],
            failure_indicators=[failure_message] if failure_message else ["Tool returned is_error=True."],
            error_details=details
            or {
                "message": failure_message or "Tool returned an error result.",
                "source": tool_name,
                "category": "tool_error",
                "retryable": False,
            },
        )

    if structured.get("success") is False and failure_message:
        return VerificationResult(
            verified=False,
            confidence=0.95,
            method="deterministic",
            evidence=f"{tool_name} reported that the action itself failed.",
            outcome="execution_failed",
            summary=failure_message,
            observed_evidence=[failure_message],
            failure_indicators=[failure_message],
            error_details=details,
        )

    return None


def _missing_expected_evidence_result(
    *,
    tool_name: str,
    expected_text: str,
    observed_text: str,
    structured: dict[str, Any],
) -> VerificationResult:
    observed: list[str] = []
    title = structured.get("page_title")
    if isinstance(title, str) and title.strip():
        observed.append(f"Page title: {title.strip()}")
    excerpt = structured.get("page_text_excerpt")
    if isinstance(excerpt, str) and excerpt.strip():
        observed.append(f"Page excerpt: {excerpt.strip()[:160]}")
    if structured.get("selector_used"):
        observed.append(f"Selector used: {structured['selector_used']}")

    failure_indicators = [f"Expected evidence '{expected_text}' was not found in the browser output."]
    if structured.get("clicked") is True:
        failure_indicators.append("The click action reported success, but the expected destination evidence was missing.")
    if structured.get("fallback_navigation") is True:
        failure_indicators.append("Fallback navigation was attempted, but expected evidence was still missing.")

    ambiguity_reason = (
        "The browser action likely progressed, but the current page evidence does not prove the expected outcome."
    )
    if not observed_text.strip():
        ambiguity_reason = "The browser output after the action was too sparse to prove or disprove the expected outcome."

    return VerificationResult(
        verified=False,
        confidence=0.0,
        method="deterministic",
        evidence=f"{tool_name} completed an action, but the expected evidence was not found.",
        outcome="evidence_missing",
        summary=ambiguity_reason,
        expected_evidence=[expected_text],
        observed_evidence=observed,
        missing_evidence=[expected_text],
        failure_indicators=failure_indicators,
        ambiguity_reason=ambiguity_reason,
    )


def _inconclusive_result(*, tool_name: str, explanation: str, observed: list[str] | None = None) -> VerificationResult:
    return VerificationResult(
        verified=False,
        confidence=0.0,
        method="deterministic",
        evidence=f"{tool_name} verification was inconclusive.",
        outcome="inconclusive",
        summary=explanation,
        observed_evidence=observed or [],
        failure_indicators=[explanation],
        ambiguity_reason=explanation,
    )


@registry.register("browser.navigate")
async def verify_browser_navigate(action_claim: dict) -> VerificationResult:
    execution_failed = _tool_execution_failed(action_claim)
    if execution_failed is not None:
        return execution_failed

    tool_name = "browser.navigate"
    structured = _structured_result(action_claim)
    expected_text = _expected_text(action_claim)
    observed_text = _combined_browser_text(action_claim)

    if expected_text:
        matched = structured.get("matched_text")
        if matched is True or expected_text in observed_text:
            observed = []
            if isinstance(structured.get("page_title"), str):
                observed.append(f"Page title: {structured['page_title']}")
            if isinstance(structured.get("page_text_excerpt"), str):
                observed.append(f"Page excerpt: {structured['page_text_excerpt'][:160]}")
            return VerificationResult(
                verified=True,
                confidence=1.0,
                method="deterministic",
                evidence="Navigation succeeded and the expected evidence was found in the resulting page state.",
                outcome="verified",
                summary=f"Found expected text '{expected_text}' after navigation.",
                expected_evidence=[expected_text],
                observed_evidence=observed or [f"Observed browser output contained '{expected_text}'."],
            )
        return _missing_expected_evidence_result(
            tool_name=tool_name,
            expected_text=expected_text,
            observed_text=observed_text,
            structured=structured,
        )

    if structured.get("success") is True or action_claim.get("claimed_success") is True:
        return VerificationResult(
            verified=True,
            confidence=0.95,
            method="deterministic",
            evidence="Navigation reported success and no additional evidence was required.",
            outcome="verified",
            summary="Navigation completed successfully.",
            observed_evidence=[f"Browser channel: {structured['browser_channel']}"] if structured.get("browser_channel") else [],
        )

    return _inconclusive_result(
        tool_name=tool_name,
        explanation="Navigation did not expose enough page evidence to prove success or failure.",
        observed=[observed_text[:160]] if observed_text else [],
    )


@registry.register("browser.fill")
async def verify_browser_fill(action_claim: dict) -> VerificationResult:
    execution_failed = _tool_execution_failed(action_claim)
    if execution_failed is not None:
        return execution_failed

    structured = _structured_result(action_claim)
    selector_used = structured.get("selector_used")
    value = action_claim.get("params", {}).get("value")
    if structured.get("filled") is True:
        observed = []
        if isinstance(selector_used, str):
            observed.append(f"Filled selector: {selector_used}")
        if isinstance(value, str) and value:
            observed.append(f"Filled value: {value}")
        return VerificationResult(
            verified=True,
            confidence=1.0,
            method="deterministic",
            evidence="Browser fill action completed and reported a concrete filled target.",
            outcome="verified",
            summary="Form field was filled successfully.",
            observed_evidence=observed,
        )

    return _inconclusive_result(
        tool_name="browser.fill",
        explanation="The fill action did not expose enough evidence to prove the field was updated.",
        observed=[f"Selector used: {selector_used}"] if isinstance(selector_used, str) else [],
    )


@registry.register("browser.click")
async def verify_browser_click(action_claim: dict) -> VerificationResult:
    execution_failed = _tool_execution_failed(action_claim)
    if execution_failed is not None:
        return execution_failed

    tool_name = "browser.click"
    structured = _structured_result(action_claim)
    expected_text = _expected_text(action_claim)
    observed_text = _combined_browser_text(action_claim)
    clicked = structured.get("clicked")

    if expected_text:
        matched = structured.get("matched_text")
        if matched is True or expected_text in observed_text:
            observed = []
            if isinstance(structured.get("selector_used"), str):
                observed.append(f"Selector used: {structured['selector_used']}")
            if isinstance(structured.get("page_title"), str):
                observed.append(f"Page title: {structured['page_title']}")
            if isinstance(structured.get("page_text_excerpt"), str):
                observed.append(f"Page excerpt: {structured['page_text_excerpt'][:160]}")
            if structured.get("fallback_navigation") is True:
                observed.append("Fallback navigation was used.")
            return VerificationResult(
                verified=True,
                confidence=1.0,
                method="deterministic",
                evidence="Browser click reached a page state that contains the expected evidence.",
                outcome="verified",
                summary=f"Found expected text '{expected_text}' after click.",
                expected_evidence=[expected_text],
                observed_evidence=observed or [f"Observed browser output contained '{expected_text}'."],
            )

        if clicked is True or structured.get("success") is True:
            return _missing_expected_evidence_result(
                tool_name=tool_name,
                expected_text=expected_text,
                observed_text=observed_text,
                structured=structured,
            )

    if clicked is True or structured.get("success") is True:
        observed = []
        if isinstance(structured.get("selector_used"), str):
            observed.append(f"Selector used: {structured['selector_used']}")
        if structured.get("skipped_click") is True:
            observed.append("Expected state was already present before retry.")
        return VerificationResult(
            verified=True,
            confidence=0.9,
            method="deterministic",
            evidence="Browser click reported a successful interaction and no stronger destination evidence was required.",
            outcome="verified",
            summary="Click action completed successfully.",
            observed_evidence=observed,
        )

    return _inconclusive_result(
        tool_name=tool_name,
        explanation="The click action did not expose enough evidence to prove the intended page transition happened.",
        observed=[observed_text[:160]] if observed_text else [],
    )
