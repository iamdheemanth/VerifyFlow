from __future__ import annotations

from pathlib import Path

from app.mcp.filesystem import FilesystemMCP
from app.registry.base import registry
from app.schemas.verification import VerificationResult


@registry.register("filesystem.write_file")
async def verify_filesystem_write_file(action_claim: dict) -> VerificationResult:
    params = action_claim.get("params", {})
    path = params.get("path")
    expected_content = params.get("content")

    file_path = Path(str(path))
    exists = file_path.exists()
    content = file_path.read_text(encoding="utf-8") if exists and file_path.is_file() else None

    if not exists:
        try:
            async with FilesystemMCP() as filesystem:
                exists = await filesystem.file_exists(path)
                content = await filesystem.read_file(path) if exists else None
        except Exception:
            exists = False
            content = None

    verified = bool(
        exists
        and content is not None
        and len(content) > 0
        and (expected_content is None or content == str(expected_content))
    )
    evidence = (
        f"File {path} exists and matches the expected content"
        if verified
        else f"File {path} was not found, was empty, or did not match the expected content"
    )
    return VerificationResult(
        verified=verified,
        confidence=1.0,
        method="deterministic",
        evidence=evidence,
    )


@registry.register("filesystem.read_file")
async def verify_filesystem_read_file(action_claim: dict) -> VerificationResult:
    result = action_claim.get("result")
    params = action_claim.get("params", {})
    expected_content = params.get("expected_content")
    verified = isinstance(result, str) and len(result) > 0
    if verified and expected_content is not None:
        verified = result == str(expected_content)
    return VerificationResult(
        verified=verified,
        confidence=1.0 if verified else 0.9,
        method="deterministic",
        evidence=(
            "Filesystem read returned the expected content"
            if verified
            else "Filesystem read returned empty, missing, or unexpected content"
        ),
    )
