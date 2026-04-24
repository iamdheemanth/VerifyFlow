from __future__ import annotations

import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest


def load_llm_module(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://vf:vf@localhost:5432/verifyflow")
    monkeypatch.setenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "executor-model")
    monkeypatch.setenv("LLM_JUDGE_MODEL", "judge-model")
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-nextauth-secret-value-32-chars")
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_OWNER", "test-owner")
    monkeypatch.setenv("MAX_RETRIES", "3")
    monkeypatch.setenv("VERIFICATION_CONFIDENCE_THRESHOLD", "0.75")

    config_module = importlib.import_module("app.core.config")
    importlib.reload(config_module)
    llm_module = importlib.import_module("app.core.llm")
    return importlib.reload(llm_module)


@pytest.mark.asyncio
async def test_chat_json_strips_markdown_fences(monkeypatch: pytest.MonkeyPatch):
    llm_module = load_llm_module(monkeypatch)

    create_mock = AsyncMock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content='```json\n{"verified": true}\n```')
                )
            ]
        )
    )
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create_mock))
    )
    async_openai_mock = Mock(return_value=fake_client)
    monkeypatch.setattr(llm_module, "AsyncOpenAI", async_openai_mock)

    client = llm_module.LLMClient(
        base_url="https://openrouter.ai/api/v1",
        api_key="test-key",
        model="executor-model",
    )

    result = await client.chat_json(
        messages=[{"role": "user", "content": "verify this"}],
        schema_hint="{verified: boolean}",
    )

    assert result == {"verified": True}
    create_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_chat_json_extracts_json_object_from_extra_text(monkeypatch: pytest.MonkeyPatch):
    llm_module = load_llm_module(monkeypatch)

    create_mock = AsyncMock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='Here is the result: {"verified": true, "confidence": 1.0}'
                    )
                )
            ]
        )
    )
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create_mock))
    )
    async_openai_mock = Mock(return_value=fake_client)
    monkeypatch.setattr(llm_module, "AsyncOpenAI", async_openai_mock)

    client = llm_module.LLMClient(
        base_url="https://openrouter.ai/api/v1",
        api_key="test-key",
        model="executor-model",
    )

    result = await client.chat_json(
        messages=[{"role": "user", "content": "verify this"}],
        schema_hint="{verified: boolean, confidence: number}",
    )

    assert result == {"verified": True, "confidence": 1.0}


@pytest.mark.asyncio
async def test_chat_retries_twice_before_success(monkeypatch: pytest.MonkeyPatch):
    llm_module = load_llm_module(monkeypatch)

    create_mock = AsyncMock(
        side_effect=[
            RuntimeError("temporary failure 1"),
            RuntimeError("temporary failure 2"),
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="success"))]
            ),
        ]
    )
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create_mock))
    )
    async_openai_mock = Mock(return_value=fake_client)
    monkeypatch.setattr(llm_module, "AsyncOpenAI", async_openai_mock)

    sleep_mock = AsyncMock()
    monkeypatch.setattr(llm_module.asyncio, "sleep", sleep_mock)

    client = llm_module.LLMClient(
        base_url="https://openrouter.ai/api/v1",
        api_key="test-key",
        model="executor-model",
    )

    result = await client.chat(messages=[{"role": "user", "content": "hello"}])

    assert result == "success"
    assert create_mock.await_count == 3
    assert sleep_mock.await_args_list[0].args == (1,)
    assert sleep_mock.await_args_list[1].args == (2,)


@pytest.mark.asyncio
async def test_chat_retries_rate_limit_errors(monkeypatch: pytest.MonkeyPatch):
    llm_module = load_llm_module(monkeypatch)

    create_mock = AsyncMock(
        side_effect=[
            RuntimeError("429 Too Many Requests"),
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="success after retry"))]
            ),
        ]
    )
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create_mock))
    )
    async_openai_mock = Mock(return_value=fake_client)
    monkeypatch.setattr(llm_module, "AsyncOpenAI", async_openai_mock)

    sleep_mock = AsyncMock()
    monkeypatch.setattr(llm_module.asyncio, "sleep", sleep_mock)

    client = llm_module.LLMClient(
        base_url="https://openrouter.ai/api/v1",
        api_key="test-key",
        model="executor-model",
    )

    result = await client.chat(messages=[{"role": "user", "content": "hello"}])

    assert result == "success after retry"
    assert create_mock.await_count == 2
    assert sleep_mock.await_count == 1


@pytest.mark.asyncio
async def test_chat_json_raises_classified_error_for_malformed_output(monkeypatch: pytest.MonkeyPatch):
    llm_module = load_llm_module(monkeypatch)

    create_mock = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="not valid json at all"))]
        )
    )
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create_mock))
    )
    async_openai_mock = Mock(return_value=fake_client)
    monkeypatch.setattr(llm_module, "AsyncOpenAI", async_openai_mock)

    client = llm_module.LLMClient(
        base_url="https://openrouter.ai/api/v1",
        api_key="test-key",
        model="executor-model",
    )

    with pytest.raises(llm_module.LLMClientError) as exc_info:
        await client.chat_json(
            messages=[{"role": "user", "content": "verify this"}],
            schema_hint="{verified: boolean}",
        )

    assert exc_info.value.category == "malformed_response"
    assert exc_info.value.retryable is False
