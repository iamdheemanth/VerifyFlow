from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.registry.base import VerificationRegistry, registry
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
