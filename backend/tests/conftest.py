from __future__ import annotations

import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("LLM_BASE_URL", "https://openrouter.ai/api/v1")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_MODEL", "executor-model")
os.environ.setdefault("LLM_JUDGE_MODEL", "judge-model")
os.environ.setdefault("NEXTAUTH_SECRET", "test-nextauth-secret-value-32-chars")
os.environ.setdefault("GITHUB_TOKEN", "test-token")
os.environ.setdefault("GITHUB_OWNER", "test-owner")
os.environ.setdefault("MAX_RETRIES", "3")
os.environ.setdefault("VERIFICATION_CONFIDENCE_THRESHOLD", "0.75")

from app.core.auth import verify_token
from app.main import app


@pytest.fixture(autouse=True)
def override_auth_dependency():
    app.dependency_overrides[verify_token] = lambda: {
        "sub": "test-user",
        "email": "test@example.com",
        "name": "Test User",
    }
    yield
    app.dependency_overrides.pop(verify_token, None)
