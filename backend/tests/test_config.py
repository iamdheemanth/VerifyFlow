from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


REQUIRED_ENV = {
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "LLM_BASE_URL": "https://openrouter.ai/api/v1",
    "LLM_API_KEY": "test-key",
    "LLM_MODEL": "executor-model",
    "LLM_JUDGE_MODEL": "judge-model",
    "NEXTAUTH_SECRET": "test-nextauth-secret-value-32-chars",
    "MAX_RETRIES": "3",
    "VERIFICATION_CONFIDENCE_THRESHOLD": "0.75",
}


def _set_required_env(monkeypatch: pytest.MonkeyPatch, **overrides: str | None) -> None:
    values = {**REQUIRED_ENV, **overrides}
    for name, value in values.items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_OWNER", raising=False)


def test_settings_require_nextauth_secret(monkeypatch: pytest.MonkeyPatch):
    _set_required_env(monkeypatch, NEXTAUTH_SECRET=None)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert "NEXTAUTH_SECRET" in str(exc_info.value)
    assert "Field required" in str(exc_info.value)


def test_settings_reject_empty_nextauth_secret(monkeypatch: pytest.MonkeyPatch):
    _set_required_env(monkeypatch, NEXTAUTH_SECRET="")

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    message = str(exc_info.value)
    assert "NEXTAUTH_SECRET is required" in message


def test_settings_reject_short_nextauth_secret(monkeypatch: pytest.MonkeyPatch):
    _set_required_env(monkeypatch, NEXTAUTH_SECRET="too-short")

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert "NEXTAUTH_SECRET must be at least 32 characters long" in str(exc_info.value)


def test_settings_reject_placeholder_llm_api_key(monkeypatch: pytest.MonkeyPatch):
    _set_required_env(monkeypatch, LLM_API_KEY="replace-with-provider-api-key")

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert "LLM_API_KEY must be set to a real secret" in str(exc_info.value)


def test_github_config_is_optional_until_github_tools_are_used(monkeypatch: pytest.MonkeyPatch):
    _set_required_env(monkeypatch)

    settings = Settings(_env_file=None)

    assert settings.github_token is None
    assert settings.github_owner is None
    with pytest.raises(RuntimeError, match="GitHub MCP tools require GITHUB_TOKEN and GITHUB_OWNER"):
        settings.require_github_config()
