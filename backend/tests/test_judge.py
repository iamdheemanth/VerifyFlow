from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("LLM_BASE_URL", "https://openrouter.ai/api/v1")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_MODEL", "executor-model")
os.environ.setdefault("LLM_JUDGE_MODEL", "judge-model")
os.environ.setdefault("GITHUB_TOKEN", "test-token")
os.environ.setdefault("GITHUB_OWNER", "test-owner")
os.environ.setdefault("MAX_RETRIES", "3")
os.environ.setdefault("VERIFICATION_CONFIDENCE_THRESHOLD", "0.75")

from app.agents import executor as executor_module
from app.agents import judge as judge_module
from app.core import llm as llm_module
from app.db.session import Base
from app.models.domain import Run, Task
from app.orchestrator.graph import route_after_decide


async def _make_session() -> tuple[AsyncSession, any]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session = session_factory()
    return session, engine


async def _seed_run_and_task(session: AsyncSession, description: str, success_criteria: str, tool_name: str):
    run_id = uuid4()
    run = Run(
        id=run_id,
        goal="Test goal",
        acceptance_criteria="Test acceptance",
        status="pending",
    )
    task = Task(
        run_id=run_id,
        index=0,
        description=description,
        success_criteria=success_criteria,
        tool_name=tool_name,
        tool_params={"repo": "demo", "path": "README.md"},
        status="claimed",
    )
    session.add(run)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return run, task


def _state_for_task(task: Task, action_claim: dict, verification_result: dict | None = None, retry_count: int = 0):
    return {
        "run_id": str(task.run_id),
        "goal": "Test goal",
        "acceptance_criteria": "Test acceptance",
        "tasks": [],
        "current_task_index": task.index,
        "current_task": {
            "id": str(task.id),
            "run_id": str(task.run_id),
            "index": task.index,
            "description": task.description,
            "success_criteria": task.success_criteria,
            "tool_name": task.tool_name,
            "tool_params": task.tool_params,
            "status": task.status,
            "claimed_result": task.claimed_result,
            "retry_count": task.retry_count,
            "created_at": task.created_at.isoformat(),
        },
        "action_claim": action_claim,
        "verification_result": verification_result,
        "retry_count": retry_count,
        "error": None,
    }


@pytest.mark.asyncio
async def test_judge_returns_verified_false_when_no_file_creation(monkeypatch: pytest.MonkeyPatch):
    session, engine = await _make_session()
    try:
        _, task = await _seed_run_and_task(
            session,
            "Create a file",
            "A file should exist after execution",
            "github.create_file",
        )
        monkeypatch.setattr(
            llm_module.judge_llm,
            "chat",
            AsyncMock(
                return_value=json.dumps(
                    {
                        "verified": False,
                        "confidence": 0.2,
                        "evidence": "No created file could be found in the claim.",
                        "failure_indicators": ["No file creation result was present"],
                        "reasoning": "The action claim did not show any created file output.",
                    }
                )
            ),
        )

        state = _state_for_task(
            task,
            action_claim={"tool_name": "github.create_file", "result": None, "claimed_success": False},
            verification_result={"verified": False, "confidence": 0.0, "method": "deterministic", "evidence": "No verifier"},
        )
        updated = await judge_module.evaluate(state, session)

        assert updated["verification_result"]["verified"] is False
        assert updated["verification_result"]["method"] == "llm_judge"
        assert updated["verification_result"]["failure_indicators"] == ["No file creation result was present"]
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_judge_returns_verified_true_for_successful_pr(monkeypatch: pytest.MonkeyPatch):
    session, engine = await _make_session()
    try:
        _, task = await _seed_run_and_task(
            session,
            "Create a pull request",
            "A pull request should be open",
            "github.create_pull_request",
        )
        monkeypatch.setattr(
            llm_module.judge_llm,
            "chat",
            AsyncMock(
                return_value=json.dumps(
                    {
                        "verified": True,
                        "confidence": 0.91,
                        "evidence": "The claim includes an open pull request with a number.",
                        "failure_indicators": [],
                        "reasoning": "The PR creation output looks consistent and includes an open PR.",
                    }
                )
            ),
        )

        state = _state_for_task(
            task,
            action_claim={
                "tool_name": "github.create_pull_request",
                "result": {"number": 42, "state": "open"},
                "claimed_success": True,
            },
            verification_result={"verified": False, "confidence": 0.0, "method": "deterministic", "evidence": "No verifier"},
        )
        updated = await judge_module.evaluate(state, session)

        assert updated["verification_result"]["verified"] is True
        assert updated["verification_result"]["confidence"] == pytest.approx(0.91)
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_retry_loop_passes_failure_indicators_back_to_executor(monkeypatch: pytest.MonkeyPatch):
    session, engine = await _make_session()
    try:
        _, task = await _seed_run_and_task(
            session,
            "Read a file",
            "The file content should be returned",
            "filesystem.read_file",
        )

        captured_messages = {}

        async def fake_chat_json(*, messages, schema_hint, temperature=0.1):
            captured_messages["messages"] = messages
            return {"tool_params": {"path": "/tmp/verifyflow/fixed.txt"}}

        monkeypatch.setattr(llm_module.executor_llm, "chat_json", fake_chat_json)
        monkeypatch.setattr(
            executor_module,
            "_call_filesystem",
            AsyncMock(return_value="file contents"),
        )

        state = _state_for_task(
            task,
            action_claim=None,
            verification_result={
                "verified": False,
                "confidence": 0.2,
                "method": "llm_judge",
                "evidence": "Previous attempt failed",
                "judge_reasoning": "The path pointed at the wrong location.",
                "failure_indicators": ["Path was incorrect", "Expected file was missing"],
            },
            retry_count=1,
        )
        updated = await executor_module.execute(state, session)

        user_message = captured_messages["messages"][1]["content"]
        assert "Path was incorrect" in user_message
        assert "Expected file was missing" in user_message
        assert updated["action_claim"]["params"] == {"path": "/tmp/verifyflow/fixed.txt"}
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_confidence_below_threshold_after_max_retries_routes_to_escalate():
    state = {
        "verification_result": {
            "verified": False,
            "confidence": 0.4,
            "method": "llm_judge",
            "evidence": "Still ambiguous",
            "judge_reasoning": "The evidence is still insufficient.",
            "failure_indicators": ["Missing expected content"],
        },
        "retry_count": 4,
    }

    assert route_after_decide(state) == "escalate"


@pytest.mark.asyncio
async def test_browser_click_records_expected_text_match_without_fallback(monkeypatch: pytest.MonkeyPatch):
    class FakeBrowser:
        async def click(self, selector: str):
            return {"is_error": False, "structured_content": {"clicked": True}, "content": []}

        async def evaluate(self, js_expression: str):
            if "document.title" in js_expression:
                return {"is_error": False, "structured_content": {"result": "English Wikipedia"}}
            return {
                "is_error": False,
                "structured_content": {"result": "The Free Encyclopedia and other content"},
            }

        async def navigate(self, url: str):
            return {"is_error": False, "structured_content": {"success": True}, "content": []}

    monkeypatch.setattr(executor_module, "_get_browser_client", AsyncMock(return_value=FakeBrowser()))

    result = await executor_module._call_browser(
        "browser.click",
        {
            "selectors": ["link=English", "text=English"],
            "expected_text": "The Free Encyclopedia",
        },
    )

    structured = result["structured_content"]
    assert structured["success"] is True
    assert structured["matched_text"] is True


@pytest.mark.asyncio
async def test_judge_returns_structured_failure_when_llm_output_is_malformed(monkeypatch: pytest.MonkeyPatch):
    session, engine = await _make_session()
    try:
        _, task = await _seed_run_and_task(
            session,
            "Verify a browser action",
            "The page should contain expected text",
            "browser.click",
        )
        monkeypatch.setattr(
            llm_module.judge_llm,
            "chat_json",
            AsyncMock(side_effect=llm_module.LLMClientError(
                "LLM response was not valid JSON: <bad output>",
                category="malformed_response",
                retryable=False,
                provider="https://openrouter.ai/api/v1",
                model="judge-model",
                raw_output="<bad output>",
            )),
        )

        state = _state_for_task(
            task,
            action_claim={"tool_name": "browser.click", "result": None, "claimed_success": False},
            verification_result={"verified": False, "confidence": 0.0, "method": "deterministic", "evidence": "No verifier"},
        )
        updated = await judge_module.evaluate(state, session)

        result = updated["verification_result"]
        assert result["verified"] is False
        assert result["method"] == "llm_judge"
        assert result["error_details"]["category"] == "malformed_response"
        assert result["error_details"]["retryable"] is False
        assert "Judge failed to produce usable verification output" in result["evidence"]
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_judge_prompt_includes_targeted_deterministic_failure_evidence(monkeypatch: pytest.MonkeyPatch):
    session, engine = await _make_session()
    try:
        _, task = await _seed_run_and_task(
            session,
            "Click the English language link",
            "The page should contain The Free Encyclopedia",
            "browser.click",
        )

        captured_messages = {}

        async def fake_chat_json(*, messages, schema_hint, temperature=0.1):
            captured_messages["messages"] = messages
            return {
                "verified": False,
                "confidence": 0.3,
                "evidence": "The expected encyclopedia heading never appeared.",
                "failure_indicators": ["Expected text was not present after the click."],
                "reasoning": "The click may have happened, but the destination evidence is still missing.",
            }

        monkeypatch.setattr(llm_module.judge_llm, "chat_json", fake_chat_json)

        state = _state_for_task(
            task,
            action_claim={
                "tool_name": "browser.click",
                "claimed_success": True,
                "params": {"selector": "link=English", "expected_text": "The Free Encyclopedia"},
            },
            verification_result={
                "verified": False,
                "confidence": 0.0,
                "method": "deterministic",
                "outcome": "evidence_missing",
                "evidence": "browser.click completed an action, but the expected evidence was not found.",
                "summary": "The browser action likely progressed, but the current page evidence does not prove the expected outcome.",
                "expected_evidence": ["The Free Encyclopedia"],
                "observed_evidence": ["Page title: Wikipedia", "Selector used: link=English"],
                "missing_evidence": ["The Free Encyclopedia"],
                "failure_indicators": ["Expected evidence 'The Free Encyclopedia' was not found in the browser output."],
                "ambiguity_reason": "The browser output after the action was too sparse to prove the expected outcome.",
            },
            retry_count=0,
        )
        await judge_module.evaluate(state, session)

        user_message = captured_messages["messages"][1]["content"]
        assert "Expected evidence:" in user_message
        assert "Missing evidence:" in user_message
        assert "Ambiguity reason:" in user_message
        assert "The Free Encyclopedia" in user_message
    finally:
        await session.close()
        await engine.dispose()
