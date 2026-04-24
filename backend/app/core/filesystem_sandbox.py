from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from app.core.config import settings


class FilesystemSandboxError(PermissionError):
    def __init__(self, message: str, *, reason: str) -> None:
        super().__init__(message)
        self.reason = reason

    def to_error_details(self, *, source: str) -> dict[str, Any]:
        return {
            "message": str(self),
            "category": "sandbox_violation",
            "retryable": False,
            "source": source,
            "reason": self.reason,
            "exception_type": self.__class__.__name__,
        }


def _coerce_path(value: str | os.PathLike[str] | None, *, missing_message: str) -> Path:
    if value is None:
        raise FilesystemSandboxError(missing_message, reason="missing_path")

    raw = os.fspath(value) if isinstance(value, os.PathLike) else str(value)
    if not raw.strip():
        raise FilesystemSandboxError(missing_message, reason="missing_path")
    if "\x00" in raw:
        raise FilesystemSandboxError(
            "Filesystem path could not be resolved safely.",
            reason="invalid_path",
        )
    return Path(raw).expanduser()


def _resolve_path(path: Path, *, invalid_message: str) -> Path:
    try:
        return path.resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        raise FilesystemSandboxError(invalid_message, reason="invalid_path") from exc


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
    except ValueError:
        return False
    return True


def resolve_allowed_base_paths(
    allowed_paths: Iterable[str | os.PathLike[str]] | None = None,
) -> list[Path]:
    configured_paths = settings.filesystem_allowed_paths if allowed_paths is None else allowed_paths
    resolved_paths: list[Path] = []

    for raw_base in configured_paths or []:
        base = _coerce_path(
            raw_base,
            missing_message="Configured filesystem allowed path is invalid.",
        )
        resolved_paths.append(
            _resolve_path(
                base,
                invalid_message="Configured filesystem allowed path is invalid.",
            )
        )

    if not resolved_paths:
        raise FilesystemSandboxError(
            "No filesystem allowed paths are configured.",
            reason="missing_allowed_paths",
        )

    return resolved_paths


def resolve_allowed_path(
    requested_path: str | os.PathLike[str] | None,
    *,
    allowed_paths: Iterable[str | os.PathLike[str]] | None = None,
) -> Path:
    requested = _coerce_path(
        requested_path,
        missing_message="Filesystem path is required.",
    )
    resolved_requested = _resolve_path(
        requested,
        invalid_message="Filesystem path could not be resolved safely.",
    )
    allowed_bases = resolve_allowed_base_paths(allowed_paths)

    if any(_is_relative_to(resolved_requested, base) for base in allowed_bases):
        return resolved_requested

    raise FilesystemSandboxError(
        "Requested filesystem path is outside configured allowed paths.",
        reason="outside_allowed_paths",
    )
