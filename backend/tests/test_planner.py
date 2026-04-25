from __future__ import annotations

import os
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
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

from app.db.session import Base
from app.models.domain import Escalation, Run, Task
from app.agents import planner


@pytest.mark.asyncio
async def test_planner_normalizes_tool_aliases(monkeypatch: pytest.MonkeyPatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    chat_json_mock = AsyncMock(
        return_value={
            "tasks": [
                {
                    "description": "Write the file",
                    "success_criteria": "File exists",
                    "tool_name": "file_write",
                    "tool_params": {"path": "/tmp/verifyflow/test.txt", "content": "hello"},
                }
            ]
        }
    )
    monkeypatch.setattr("app.core.llm.executor_llm.chat_json", chat_json_mock)

    state = {
        "run_id": str(uuid4()),
        "goal": 'Create a file called test.txt in /tmp/verifyflow with the content "hello"',
        "acceptance_criteria": "The file exists.",
        "tasks": [],
        "current_task_index": -1,
        "current_task": None,
        "action_claim": None,
        "verification_result": None,
        "retry_count": 0,
        "error": None,
    }

    async with session_factory() as session:
        planned_state = await planner.plan(state, session)
        persisted = (await session.execute(Task.__table__.select())).mappings().all()

    assert planned_state["tasks"][0]["tool_name"] == "filesystem.write_file"
    assert persisted[0]["tool_name"] == "filesystem.write_file"

    await engine.dispose()


@pytest.mark.asyncio
async def test_planner_falls_back_when_llm_json_is_invalid(monkeypatch: pytest.MonkeyPatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    chat_json_mock = AsyncMock(side_effect=ValueError("LLM response was not valid JSON: <empty response>"))
    monkeypatch.setattr("app.core.llm.executor_llm.chat_json", chat_json_mock)

    state = {
        "run_id": str(uuid4()),
        "goal": 'Create a file called test.txt in /tmp/verifyflow with the content "hello from VerifyFlow"',
        "acceptance_criteria": "The file exists and has the requested content.",
        "tasks": [],
        "current_task_index": -1,
        "current_task": None,
        "action_claim": None,
        "verification_result": None,
        "retry_count": 0,
        "error": None,
    }

    async with session_factory() as session:
        planned_state = await planner.plan(state, session)

    assert planned_state["tasks"]
    assert planned_state["tasks"][0]["tool_name"] == "filesystem.write_file"
    assert planned_state["tasks"][0]["tool_params"]["path"] == "/tmp/verifyflow/test.txt"
    assert planned_state["tasks"][0]["tool_params"]["content"] == "hello from VerifyFlow"

    await engine.dispose()


@pytest.mark.asyncio
async def test_planner_uses_deterministic_filesystem_plan_without_llm(monkeypatch: pytest.MonkeyPatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    chat_json_mock = AsyncMock(side_effect=AssertionError("LLM should not be called"))
    monkeypatch.setattr("app.core.llm.executor_llm.chat_json", chat_json_mock)

    state = {
        "run_id": str(uuid4()),
        "goal": r'Create the file C:\Temp\verifyflow\hello.txt with the exact content "hello from VerifyFlow"',
        "acceptance_criteria": r'The file exists at C:\Temp\verifyflow\hello.txt and reading it returns exactly "hello from VerifyFlow".',
        "tasks": [],
        "current_task_index": -1,
        "current_task": None,
        "action_claim": None,
        "verification_result": None,
        "retry_count": 0,
        "error": None,
    }

    async with session_factory() as session:
        planned_state = await planner.plan(state, session)

    assert len(planned_state["tasks"]) == 2
    assert planned_state["tasks"][0]["tool_name"] == "filesystem.write_file"
    assert planned_state["tasks"][1]["tool_name"] == "filesystem.read_file"
    assert planned_state["tasks"][0]["tool_params"]["path"] == r"C:\Temp\verifyflow\hello.txt"

    await engine.dispose()


@pytest.mark.asyncio
async def test_planner_falls_back_when_llm_request_errors(monkeypatch: pytest.MonkeyPatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    chat_json_mock = AsyncMock(side_effect=RuntimeError("404 model not found"))
    monkeypatch.setattr("app.core.llm.executor_llm.chat_json", chat_json_mock)

    state = {
        "run_id": str(uuid4()),
        "goal": 'Navigate to https://example.com and confirm the page shows the heading Example Domain',
        "acceptance_criteria": 'The browser opens https://example.com successfully and the visible page text includes Example Domain.',
        "tasks": [],
        "current_task_index": -1,
        "current_task": None,
        "action_claim": None,
        "verification_result": None,
        "retry_count": 0,
        "error": None,
    }

    async with session_factory() as session:
        planned_state = await planner.plan(state, session)

    assert planned_state["tasks"]
    assert planned_state["tasks"][0]["tool_name"] == "browser.navigate"
    assert planned_state["tasks"][0]["tool_params"]["url"] == "https://example.com"

    await engine.dispose()


@pytest.mark.asyncio
async def test_planner_escalates_unsupported_plan_without_filesystem_placeholder(
    monkeypatch: pytest.MonkeyPatch,
):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    chat_json_mock = AsyncMock(
        return_value={
            "tasks": [
                {
                    "description": "Book a flight",
                    "success_criteria": "The ticket is booked",
                    "tool_name": "travel.book_flight",
                    "tool_params": {"destination": "Mars"},
                }
            ]
        }
    )
    monkeypatch.setattr("app.core.llm.executor_llm.chat_json", chat_json_mock)

    run_id = uuid4()
    state = {
        "run_id": str(run_id),
        "goal": "Book a flight to Mars using the travel desk.",
        "acceptance_criteria": "A confirmed itinerary is available.",
        "tasks": [],
        "current_task_index": -1,
        "current_task": None,
        "action_claim": None,
        "verification_result": None,
        "retry_count": 0,
        "error": None,
    }

    async with session_factory() as session:
        session.add(
            Run(
                id=run_id,
                goal=state["goal"],
                acceptance_criteria=state["acceptance_criteria"],
                status="pending",
            )
        )
        await session.commit()

        planned_state = await planner.plan(state, session)
        persisted_run = (await session.execute(select(Run).where(Run.id == run_id))).scalar_one()
        tasks = (await session.execute(select(Task).where(Task.run_id == run_id))).scalars().all()
        escalations = (await session.execute(select(Escalation).where(Escalation.run_id == run_id))).scalars().all()

    assert planned_state["decision"] == "finish"
    assert planned_state["error"] == "Planner could not create an executable plan. Manual review is required."
    assert persisted_run.status == "failed"
    assert persisted_run.failure_record["category"] == "planning_failed"
    assert persisted_run.failure_record["original_goal"] == state["goal"]
    assert "travel.book_flight" in persisted_run.failure_record["planner_reason"]
    assert len(tasks) == 1
    assert tasks[0].status == "escalated"
    assert tasks[0].tool_name == "planner.manual_review"
    assert tasks[0].tool_params["planning_failure"]["suggested_next_action"]
    assert tasks[0].tool_params["planning_failure"].get("path") is None
    assert tasks[0].tool_name != "filesystem.write_file"
    assert len(escalations) == 1
    assert escalations[0].status == "pending_review"
    assert escalations[0].evidence_bundle["category"] == "planning_failed"

    await engine.dispose()


def test_extract_url_from_text_trims_trailing_punctuation():
    url = planner._extract_url_from_text(
        "Navigate to https://www.wikipedia.org, click the English language link."
    )
    assert url == "https://www.wikipedia.org"


@pytest.mark.asyncio
async def test_planner_uses_deterministic_browser_plan_for_click_flows(
    monkeypatch: pytest.MonkeyPatch,
):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    chat_json_mock = AsyncMock(side_effect=AssertionError("LLM should not be called"))
    monkeypatch.setattr("app.core.llm.executor_llm.chat_json", chat_json_mock)

    state = {
        "run_id": str(uuid4()),
        "goal": "Navigate to https://www.wikipedia.org, click the English language link, and verify that the destination page contains The Free Encyclopedia",
        "acceptance_criteria": "The browser opens wikipedia.org and the destination page contains The Free Encyclopedia.",
        "tasks": [],
        "current_task_index": -1,
        "current_task": None,
        "action_claim": None,
        "verification_result": None,
        "retry_count": 0,
        "error": None,
    }

    async with session_factory() as session:
        planned_state = await planner.plan(state, session)

    assert planned_state["tasks"][0]["tool_params"]["url"] == "https://www.wikipedia.org"
    assert [task["tool_name"] for task in planned_state["tasks"]] == ["browser.navigate", "browser.click"]

    await engine.dispose()


@pytest.mark.asyncio
async def test_planner_uses_deterministic_duckduckgo_search_plan(
    monkeypatch: pytest.MonkeyPatch,
):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    chat_json_mock = AsyncMock(side_effect=AssertionError("LLM should not be called"))
    monkeypatch.setattr("app.core.llm.executor_llm.chat_json", chat_json_mock)

    state = {
        "run_id": str(uuid4()),
        "goal": "Navigate to https://duckduckgo.com, search for Wikipedia, and verify that the results page contains the text Wikipedia",
        "acceptance_criteria": "The browser opens https://duckduckgo.com, submits a search for Wikipedia, and the visible results page contains the text Wikipedia.",
        "tasks": [],
        "current_task_index": -1,
        "current_task": None,
        "action_claim": None,
        "verification_result": None,
        "retry_count": 0,
        "error": None,
    }

    async with session_factory() as session:
        planned_state = await planner.plan(state, session)

    assert [task["tool_name"] for task in planned_state["tasks"]] == ["browser.navigate"]
    assert planned_state["tasks"][0]["tool_params"]["url"] == "https://duckduckgo.com/?q=Wikipedia"
    assert planned_state["tasks"][0]["tool_params"]["expected_text"] == "Wikipedia"

    await engine.dispose()


@pytest.mark.asyncio
async def test_planner_uses_deterministic_google_results_plan(
    monkeypatch: pytest.MonkeyPatch,
):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    chat_json_mock = AsyncMock(side_effect=AssertionError("LLM should not be called"))
    monkeypatch.setattr("app.core.llm.executor_llm.chat_json", chat_json_mock)

    state = {
        "run_id": str(uuid4()),
        "goal": "Navigate to https://www.google.com/search?q=OpenAI and verify that the results page contains the text OpenAI",
        "acceptance_criteria": "The browser opens the Google search results page for OpenAI and the visible page text or page title contains OpenAI.",
        "tasks": [],
        "current_task_index": -1,
        "current_task": None,
        "action_claim": None,
        "verification_result": None,
        "retry_count": 0,
        "error": None,
    }

    async with session_factory() as session:
        planned_state = await planner.plan(state, session)

    assert [task["tool_name"] for task in planned_state["tasks"]] == ["browser.navigate"]
    assert planned_state["tasks"][0]["tool_params"]["url"] == "https://www.google.com/search?q=OpenAI"
    assert planned_state["tasks"][0]["tool_params"]["expected_text"] == "OpenAI"

    await engine.dispose()


@pytest.mark.asyncio
async def test_planner_uses_generic_click_plan_without_llm(
    monkeypatch: pytest.MonkeyPatch,
):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    chat_json_mock = AsyncMock(side_effect=AssertionError("LLM should not be called"))
    monkeypatch.setattr("app.core.llm.executor_llm.chat_json", chat_json_mock)

    state = {
        "run_id": str(uuid4()),
        "goal": "Navigate to https://www.wikipedia.org, click the English language link, and verify that the destination page contains The Free Encyclopedia",
        "acceptance_criteria": "The browser opens wikipedia.org and the destination page contains The Free Encyclopedia.",
        "tasks": [],
        "current_task_index": -1,
        "current_task": None,
        "action_claim": None,
        "verification_result": None,
        "retry_count": 0,
        "error": None,
    }

    async with session_factory() as session:
        planned_state = await planner.plan(state, session)

    assert [task["tool_name"] for task in planned_state["tasks"]] == ["browser.navigate", "browser.click"]
    assert planned_state["tasks"][1]["tool_params"]["selectors"][0] == "link=English language"

    await engine.dispose()


@pytest.mark.asyncio
async def test_planner_uses_generic_search_plan_without_llm(
    monkeypatch: pytest.MonkeyPatch,
):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    chat_json_mock = AsyncMock(side_effect=AssertionError("LLM should not be called"))
    monkeypatch.setattr("app.core.llm.executor_llm.chat_json", chat_json_mock)

    state = {
        "run_id": str(uuid4()),
        "goal": "Navigate to https://news.ycombinator.com, search for OpenAI, and verify that the page contains OpenAI",
        "acceptance_criteria": "The browser opens the site, submits a search for OpenAI, and the resulting page contains OpenAI.",
        "tasks": [],
        "current_task_index": -1,
        "current_task": None,
        "action_claim": None,
        "verification_result": None,
        "retry_count": 0,
        "error": None,
    }

    async with session_factory() as session:
        planned_state = await planner.plan(state, session)

    assert [task["tool_name"] for task in planned_state["tasks"]] == ["browser.navigate", "browser.fill", "browser.click"]
    assert planned_state["tasks"][1]["tool_params"]["value"] == "OpenAI"
    assert "button=Search" in planned_state["tasks"][2]["tool_params"]["selectors"]

    await engine.dispose()
