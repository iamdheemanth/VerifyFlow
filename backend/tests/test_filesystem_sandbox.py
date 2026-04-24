from __future__ import annotations

import pytest

from app.agents import executor as executor_module
from app.core.config import settings
from app.core.filesystem_sandbox import FilesystemSandboxError
from app.registry.base import DeterministicVerifierError, registry


@pytest.fixture
def allowed_root(tmp_path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "allowed"
    root.mkdir()
    monkeypatch.setattr(settings, "filesystem_allowed_paths", [str(root)])
    return root


@pytest.mark.asyncio
async def test_filesystem_write_inside_allowed_directory_succeeds(allowed_root):
    target = allowed_root / "nested" / "proof.txt"

    result = await executor_module._call_filesystem(
        "filesystem.write_file",
        {"path": str(target), "content": "ok"},
    )

    assert result["is_error"] is False
    assert result["structured_content"]["written"] is True
    assert target.read_text(encoding="utf-8") == "ok"


@pytest.mark.asyncio
async def test_filesystem_write_outside_allowed_directory_fails(tmp_path, allowed_root):
    target = tmp_path / "outside.txt"

    with pytest.raises(FilesystemSandboxError) as exc_info:
        await executor_module._call_filesystem(
            "filesystem.write_file",
            {"path": str(target), "content": "blocked"},
        )

    assert not target.exists()
    assert "outside configured allowed paths" in str(exc_info.value)
    details = exc_info.value.to_error_details(source="filesystem.write_file")
    assert details["category"] == "sandbox_violation"
    assert details["retryable"] is False
    assert str(target) not in details["message"]


@pytest.mark.asyncio
async def test_filesystem_write_path_traversal_outside_allowed_directory_fails(tmp_path, allowed_root):
    target = allowed_root / ".." / "traversed.txt"
    escaped_target = tmp_path / "traversed.txt"

    with pytest.raises(FilesystemSandboxError):
        await executor_module._call_filesystem(
            "filesystem.write_file",
            {"path": str(target), "content": "blocked"},
        )

    assert not escaped_target.exists()


@pytest.mark.asyncio
async def test_filesystem_write_symlink_escape_fails(tmp_path, allowed_root):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = allowed_root / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"Symlink creation is not supported in this environment: {exc}")

    escaped_target = outside / "escape.txt"

    with pytest.raises(FilesystemSandboxError):
        await executor_module._call_filesystem(
            "filesystem.write_file",
            {"path": str(link / "escape.txt"), "content": "blocked"},
        )

    assert not escaped_target.exists()


@pytest.mark.asyncio
async def test_filesystem_write_verifier_rejects_outside_allowed_file(tmp_path, allowed_root):
    target = tmp_path / "outside-proof.txt"
    target.write_text("secret", encoding="utf-8")

    with pytest.raises(DeterministicVerifierError) as exc_info:
        await registry.verify(
            {
                "tool_name": "filesystem.write_file",
                "params": {"path": str(target), "content": "secret"},
                "result": {"written": True},
                "claimed_success": True,
            }
        )

    assert exc_info.value.category == "sandbox_violation"
    assert exc_info.value.retryable is False
    assert str(target) not in str(exc_info.value)


@pytest.mark.asyncio
async def test_filesystem_read_verifier_rejects_outside_allowed_file(tmp_path, allowed_root):
    target = tmp_path / "outside-read.txt"
    target.write_text("secret", encoding="utf-8")

    with pytest.raises(DeterministicVerifierError) as exc_info:
        await registry.verify(
            {
                "tool_name": "filesystem.read_file",
                "params": {"path": str(target), "expected_content": "secret"},
                "result": "secret",
                "claimed_success": True,
            }
        )

    assert exc_info.value.category == "sandbox_violation"
    assert exc_info.value.retryable is False
    assert str(target) not in str(exc_info.value)
