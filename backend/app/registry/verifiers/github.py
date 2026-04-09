from __future__ import annotations

from typing import Any

from app.mcp.github import GitHubMCP
from app.registry.base import registry
from app.schemas.verification import VerificationResult


def _extract_pr_number(result: Any) -> int | None:
    if isinstance(result, dict):
        for key in ("number", "pr_number", "pull_number"):
            value = result.get(key)
            if isinstance(value, int):
                return value

        structured = result.get("structured_content")
        if isinstance(structured, dict):
            return _extract_pr_number(structured)

        content = result.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        digits = "".join(char for char in text if char.isdigit())
                        if digits:
                            return int(digits)
    return None


@registry.register("github.create_file")
async def verify_github_create_file(action_claim: dict) -> VerificationResult:
    params = action_claim.get("params", {})
    repo = params.get("repo")
    path = params.get("path")

    async with GitHubMCP() as github:
        file_result = await github.get_file(repo, path)

    verified = file_result is not None
    evidence = (
        f"File {path} found in {repo}" if verified else f"File {path} not found in {repo}"
    )
    return VerificationResult(
        verified=verified,
        confidence=1.0,
        method="deterministic",
        evidence=evidence,
    )


@registry.register("github.create_pull_request")
async def verify_github_create_pull_request(action_claim: dict) -> VerificationResult:
    params = action_claim.get("params", {})
    repo = params.get("repo")
    result = action_claim.get("result", {})
    pr_number = _extract_pr_number(result)

    if pr_number is None:
        return VerificationResult(
            verified=False,
            confidence=1.0,
            method="deterministic",
            evidence="PR not found",
        )

    async with GitHubMCP() as github:
        pr = await github.get_pull_request(repo, pr_number)

    if not pr:
        return VerificationResult(
            verified=False,
            confidence=1.0,
            method="deterministic",
            evidence="PR not found",
        )

    state = None
    structured = pr.get("structured_content") if isinstance(pr, dict) else None
    if isinstance(structured, dict):
        state = structured.get("state")
    if state is None and isinstance(pr, dict):
        state = pr.get("state")

    verified = state != "closed"
    evidence = f"PR #{pr_number} is {state}" if state else "PR not found"
    return VerificationResult(
        verified=verified,
        confidence=1.0,
        method="deterministic",
        evidence=evidence,
    )


@registry.register("github.get_file")
async def verify_github_get_file(action_claim: dict) -> VerificationResult:
    params = action_claim.get("params", {})
    repo = params.get("repo")
    path = params.get("path")
    expected_content = params.get("expected_content")

    async with GitHubMCP() as github:
        file_result = await github.get_file(repo, path)

    if file_result is None:
        return VerificationResult(
            verified=False,
            confidence=1.0,
            method="deterministic",
            evidence=f"File {path} not found in {repo}",
        )

    if expected_content is None:
        return VerificationResult(
            verified=True,
            confidence=1.0,
            method="deterministic",
            evidence=f"File {path} found in {repo}",
        )

    actual_text = ""
    content = file_result.get("content") if isinstance(file_result, dict) else None
    if isinstance(content, list):
        text_parts = [
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and isinstance(item.get("text"), str)
        ]
        actual_text = "\n".join(text_parts)

    verified = expected_content in actual_text
    evidence = (
        f"File {path} content matched expected value"
        if verified
        else f"File {path} content did not match expected value"
    )
    return VerificationResult(
        verified=verified,
        confidence=1.0,
        method="deterministic",
        evidence=evidence,
    )
