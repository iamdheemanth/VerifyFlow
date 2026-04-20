from __future__ import annotations

from pathlib import Path

from app.mcp.filesystem import FilesystemMCP
from app.registry.base import coerce_verifier_exception, registry
from app.schemas.verification import VerificationResult


@registry.register("filesystem.write_file")
async def verify_filesystem_write_file(action_claim: dict) -> VerificationResult:
    params = action_claim.get("params", {})
    path = params.get("path")
    expected_content = params.get("content")

    try:
        file_path = Path(str(path))
        exists = file_path.exists()
        content = file_path.read_text(encoding="utf-8") if exists and file_path.is_file() else None

        if not exists:
            try:
                async with FilesystemMCP() as filesystem:
                    exists = await filesystem.file_exists(path)
                    content = await filesystem.read_file(path) if exists else None
            except Exception as exc:
                raise coerce_verifier_exception(exc, tool_name="filesystem.write_file") from exc
    except Exception as exc:
        if isinstance(exc, OSError):
            raise coerce_verifier_exception(exc, tool_name="filesystem.write_file") from exc
        raise

    verified = bool(
        exists
        and content is not None
        and len(content) > 0
        and (expected_content is None or content == str(expected_content))
    )
    if verified:
        return VerificationResult(
            verified=True,
            confidence=1.0,
            method="deterministic",
            evidence=f"File {path} exists and matches the expected content.",
            outcome="verified",
            summary="Filesystem write produced the expected file contents.",
            expected_evidence=[f"File {path} exists."],
            observed_evidence=[f"Read back {len(content or '')} characters from {path}."],
        )

    missing: list[str] = []
    observed: list[str] = []
    if not exists:
        missing.append(f"File {path} exists.")
    else:
        observed.append(f"File {path} exists.")
    if exists and (content is None or len(content) == 0):
        missing.append("File content is non-empty.")
    if expected_content is not None and content is not None and content != str(expected_content):
        missing.append("File content matches the expected content exactly.")
        observed.append("File content was present but did not match the expected value.")

    return VerificationResult(
        verified=False,
        confidence=1.0,
        method="deterministic",
        evidence=f"File {path} was not found, was empty, or did not match the expected content.",
        outcome="execution_failed" if not exists else "evidence_missing",
        summary="Filesystem verification could not prove the requested file state.",
        expected_evidence=[f"File {path} exists and matches the expected content."],
        observed_evidence=observed,
        missing_evidence=missing,
        failure_indicators=missing or ["Filesystem verification failed."],
    )


@registry.register("filesystem.read_file")
async def verify_filesystem_read_file(action_claim: dict) -> VerificationResult:
    result = action_claim.get("result")
    params = action_claim.get("params", {})
    expected_content = params.get("expected_content")
    verified = isinstance(result, str) and len(result) > 0
    if verified and expected_content is not None:
        verified = result == str(expected_content)
    if verified:
        return VerificationResult(
            verified=True,
            confidence=1.0,
            method="deterministic",
            evidence="Filesystem read returned the expected content.",
            outcome="verified",
            summary="Filesystem read produced the expected content.",
            observed_evidence=[f"Returned {len(result)} characters."],
        )
    return VerificationResult(
        verified=False,
        confidence=0.95,
        method="deterministic",
        evidence="Filesystem read returned empty, missing, or unexpected content.",
        outcome="evidence_missing",
        summary="Filesystem read returned content that did not satisfy the expected evidence.",
        missing_evidence=["Expected file content was not returned."],
        failure_indicators=["Filesystem read returned empty, missing, or unexpected content."],
    )
