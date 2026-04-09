from __future__ import annotations

from app.mcp.filesystem import FilesystemMCP
from app.registry.base import registry
from app.schemas.verification import VerificationResult


@registry.register("filesystem.write_file")
async def verify_filesystem_write_file(action_claim: dict) -> VerificationResult:
    params = action_claim.get("params", {})
    path = params.get("path")

    async with FilesystemMCP() as filesystem:
        exists = await filesystem.file_exists(path)
        content = await filesystem.read_file(path) if exists else None

    verified = bool(exists and content and len(content) > 0)
    evidence = (
        f"File {path} exists with non-empty content"
        if verified
        else f"File {path} was not found or is empty"
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
    verified = isinstance(result, str) and len(result) > 0
    return VerificationResult(
        verified=verified,
        confidence=1.0 if verified else 0.9,
        method="deterministic",
        evidence=(
            "Filesystem read returned non-empty content"
            if verified
            else "Filesystem read returned empty or missing content"
        ),
    )
