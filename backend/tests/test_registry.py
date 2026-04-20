from __future__ import annotations

import os
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("LLM_BASE_URL", "https://openrouter.ai/api/v1")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_MODEL", "executor-model")
os.environ.setdefault("LLM_JUDGE_MODEL", "judge-model")
os.environ.setdefault("GITHUB_TOKEN", "test-token")
os.environ.setdefault("GITHUB_OWNER", "test-owner")
os.environ.setdefault("MAX_RETRIES", "3")
os.environ.setdefault("VERIFICATION_CONFIDENCE_THRESHOLD", "0.75")

from app.registry.base import DeterministicVerifierError, VerificationRegistry, registry
from app.registry.verifiers.browser import verify_browser_click
from app.registry.verifiers import github as github_verifiers
from app.schemas.verification import VerificationResult


@pytest.mark.asyncio
async def test_register_and_call_verifier_returns_verification_result():
    test_registry = VerificationRegistry()

    @test_registry.register("test.tool")
    async def verifier(action_claim: dict) -> VerificationResult:
        return VerificationResult(
            verified=action_claim["result"] == "ok",
            confidence=1.0,
            method="deterministic",
            evidence="Verifier executed",
        )

    result = await test_registry.verify({"tool_name": "test.tool", "result": "ok"})

    assert result.verified is True
    assert result.confidence == 1.0
    assert result.method == "deterministic"


@pytest.mark.asyncio
async def test_unregistered_tool_returns_zero_confidence_and_needs_judge():
    test_registry = VerificationRegistry()

    result = await test_registry.verify({"tool_name": "unknown.tool"})

    assert result.verified is False
    assert result.confidence == 0.0
    assert result.outcome == "inconclusive"
    assert test_registry.needs_judge(result) is True


@pytest.mark.asyncio
async def test_github_file_verifier_returns_verified_when_file_exists(monkeypatch: pytest.MonkeyPatch):
    github_client = AsyncMock()
    github_client.__aenter__.return_value.get_file = AsyncMock(
        return_value={"content": [{"type": "text", "text": "hello"}]}
    )
    github_client.__aexit__.return_value = None
    monkeypatch.setattr(github_verifiers, "GitHubMCP", lambda: github_client)

    result = await registry.verify(
        {
            "tool_name": "github.create_file",
            "params": {"repo": "demo", "path": "README.md"},
            "result": {},
        }
    )

    assert result.verified is True
    assert result.confidence == 1.0
    assert "README.md" in result.evidence


@pytest.mark.asyncio
async def test_github_verifier_wraps_transient_mcp_failure_as_retryable(monkeypatch: pytest.MonkeyPatch):
    github_client = AsyncMock()
    github_client.__aenter__.side_effect = TimeoutError("Timed out while initializing GitHub MCP session")
    github_client.__aexit__.return_value = None
    monkeypatch.setattr(github_verifiers, "GitHubMCP", lambda: github_client)

    with pytest.raises(DeterministicVerifierError) as exc_info:
        await registry.verify(
            {
                "tool_name": "github.get_file",
                "params": {"repo": "demo", "path": "README.md"},
                "result": {},
            }
        )

    assert exc_info.value.retryable is True
    assert exc_info.value.tool_name == "github.get_file"


@pytest.mark.asyncio
async def test_browser_click_verifier_checks_expected_text_in_result():
    result = await verify_browser_click(
        {
            "tool_name": "browser.click",
            "params": {"selector": 'button[type="submit"]', "expected_text": "Wikipedia"},
            "claimed_success": True,
            "result": {
                "is_error": False,
                "structured_content": {
                    "success": True,
                    "page_title": "Wikipedia - DuckDuckGo",
                    "matched_text": True,
                },
                "content": [{"type": "text", "text": "Wikipedia results loaded"}],
            },
        }
    )

    assert result.verified is True
    assert result.confidence == 1.0
    assert result.outcome == "verified"
    assert "Wikipedia" in result.summary


@pytest.mark.asyncio
async def test_browser_click_verifier_distinguishes_missing_evidence_from_execution_failure():
    result = await verify_browser_click(
        {
            "tool_name": "browser.click",
            "params": {"selector": "link=English", "expected_text": "The Free Encyclopedia"},
            "claimed_success": True,
            "result": {
                "is_error": False,
                "structured_content": {
                    "clicked": True,
                    "success": False,
                    "selector_used": "link=English",
                    "page_title": "Wikipedia",
                    "page_text_excerpt": "Wikipedia portal and language links",
                },
                "content": [{"type": "text", "text": "Wikipedia portal and language links"}],
            },
        }
    )

    assert result.verified is False
    assert result.outcome == "evidence_missing"
    assert result.confidence == 0.0
    assert "The Free Encyclopedia" in result.missing_evidence


@pytest.mark.asyncio
async def test_browser_click_verifier_returns_execution_failed_for_explicit_tool_error():
    result = await verify_browser_click(
        {
            "tool_name": "browser.click",
            "params": {"selector": "text=English"},
            "claimed_success": False,
            "error": "Element not found",
            "error_details": {
                "message": "Element not found",
                "category": "tool_error",
                "retryable": False,
                "source": "browser.click",
            },
            "result": None,
        }
    )

    assert result.verified is False
    assert result.outcome == "execution_failed"
    assert result.confidence >= 0.95
    assert "Element not found" in result.failure_indicators


@pytest.mark.asyncio
async def test_browser_fill_verifier_returns_full_confidence_on_success():
    result = await registry.verify(
        {
            "tool_name": "browser.fill",
            "params": {"selectors": ['input[name="q"]'], "value": "Wikipedia"},
            "claimed_success": True,
            "result": {
                "is_error": False,
                "structured_content": {"filled": True, "selector_used": 'input[name="q"]'},
            },
        }
    )

    assert result.verified is True
    assert result.confidence == 1.0
    assert result.outcome == "verified"


@pytest.mark.asyncio
async def test_registry_wraps_transient_verifier_exception_with_retryable_details():
    test_registry = VerificationRegistry()

    @test_registry.register("test.timeout")
    async def verifier(action_claim: dict) -> VerificationResult:
        raise TimeoutError("Timed out while querying deterministic verifier backend")

    with pytest.raises(DeterministicVerifierError) as exc_info:
        await test_registry.verify({"tool_name": "test.timeout"})

    assert exc_info.value.retryable is True
    assert exc_info.value.category == "timeout"
    assert exc_info.value.tool_name == "test.timeout"


def test_needs_judge_skips_deterministic_verifier_infrastructure_failures():
    test_registry = VerificationRegistry()
    result = VerificationResult(
        verified=False,
        confidence=0.0,
        method="deterministic",
        evidence="Deterministic verifier could not complete because the verifier-side dependency failed transiently.",
        outcome="inconclusive",
        summary="Timed out while querying deterministic verifier backend",
        error_details={
            "message": "Timed out while querying deterministic verifier backend",
            "category": "timeout",
            "retryable": True,
            "tool_name": "github.get_file",
            "source": "deterministic_verifier",
        },
    )

    assert test_registry.needs_judge(result) is False
