from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.browser import BrowserMCP
from app.mcp.filesystem import FilesystemMCP
from app.mcp.github import GitHubMCP
from app.mcp import MCPToolError
from app.models.domain import Task, utcnow
from app.orchestrator.states import VerifyFlowState
from app.core.filesystem_sandbox import resolve_allowed_path
from app.services import reliability

_browser_clients: dict[str, BrowserMCP] = {}
_active_browser_channel: str | None = None


async def _load_task(db: AsyncSession, task_id: str) -> Task:
    result = await db.execute(select(Task).where(Task.id == UUID(task_id)))
    return result.scalar_one()


async def reset_browser_clients() -> None:
    global _active_browser_channel
    for client in list(_browser_clients.values()):
        try:
            await client.__aexit__(None, None, None)
        except Exception:
            continue
    _browser_clients.clear()
    _active_browser_channel = None


async def _get_browser_client(channel: str) -> BrowserMCP:
    client = _browser_clients.get(channel)
    if client is not None:
        return client

    client = BrowserMCP(channel=channel)
    await client.__aenter__()
    _browser_clients[channel] = client
    return client


async def _call_github(tool_name: str, params: dict[str, Any]) -> Any:
    async with GitHubMCP() as github:
        if tool_name == "github.create_file":
            return await github.create_file(**params)
        if tool_name == "github.get_file":
            return await github.get_file(**params)
        if tool_name == "github.create_pull_request":
            return await github.create_pull_request(**params)
    raise ValueError(f"Unsupported GitHub tool: {tool_name}")


async def _call_filesystem(tool_name: str, params: dict[str, Any]) -> Any:
    path = resolve_allowed_path(params.get("path"))
    if tool_name == "filesystem.write_file":
        content = str(params.get("content", ""))
        path.parent.mkdir(parents=True, exist_ok=True)
        path = resolve_allowed_path(path)
        await asyncio.to_thread(path.write_text, content, encoding="utf-8")
        return {
            "is_error": False,
            "structured_content": {"path": str(path), "written": True},
            "content": [{"type": "text", "text": f"Wrote {path}"}],
            "fallback": "local_filesystem",
        }
    if tool_name == "filesystem.read_file":
        if not path.exists():
            try:
                async with FilesystemMCP() as filesystem:
                    return await filesystem.read_file(path=str(path))
            except Exception:
                return None
        return await asyncio.to_thread(path.read_text, encoding="utf-8")

    raise ValueError(f"Unsupported filesystem tool: {tool_name}")


async def _call_browser(tool_name: str, params: dict[str, Any]) -> Any:
    from app.core.config import settings

    global _active_browser_channel
    last_error: Exception | None = None
    configured_channels = settings.browser_channels or ["msedge", "chrome", "chromium"]
    if _active_browser_channel and _active_browser_channel in configured_channels:
        channels = [_active_browser_channel]
    else:
        channels = configured_channels

    for channel in channels:
        try:
            browser = await _get_browser_client(channel)
            _active_browser_channel = channel
            if tool_name == "browser.navigate":
                url = str(params.get("url", ""))
                expected_text = params.get("expected_text")
                result = await browser.navigate(url=url)
                structured = result.get("structured_content")
                if not isinstance(structured, dict):
                    structured = {}
                structured["browser_channel"] = channel
                if expected_text:
                    page_text = None
                    page_title = None
                    for _ in range(3):
                        page_title, page_text = await _read_browser_page(browser)
                        if isinstance(page_text, str) and page_text.strip():
                            break
                        await asyncio.sleep(1)

                    expected = str(expected_text)
                    matched = _page_matches_expected(expected, page_title, page_text)
                    structured.update(
                        {
                            "success": matched,
                            "expected_text": str(expected_text),
                            "matched_text": matched,
                            "page_title": page_title,
                            "page_text_excerpt": page_text[:200] if isinstance(page_text, str) else None,
                        }
                    )
                result["structured_content"] = structured
                return result
            if tool_name == "browser.fill":
                selectors = params.get("selectors")
                selector_values = selectors if isinstance(selectors, list) and selectors else [params.get("selector", "")]
                last_result: Any = None
                for selector in selector_values:
                    result = await browser.fill(selector=str(selector), value=str(params.get("value", "")))
                    structured = result.get("structured_content")
                    if not isinstance(structured, dict):
                        structured = {}
                    structured["browser_channel"] = channel
                    structured["selector_used"] = str(selector)
                    result["structured_content"] = structured
                    last_result = result
                    if structured.get("filled") is True:
                        return result
                return last_result
            if tool_name == "browser.click":
                selectors = params.get("selectors")
                selector_values = selectors if isinstance(selectors, list) and selectors else [params.get("selector", "")]
                expected_text = params.get("expected_text")
                fallback_url = params.get("fallback_url")
                result = None
                structured: dict[str, Any] = {}
                selector_used = None
                if isinstance(expected_text, str) and expected_text.strip():
                    page_title, page_text = await _read_browser_page(browser)
                    expected = str(expected_text)
                    if _page_matches_expected(expected, page_title, page_text):
                        return {
                            "is_error": False,
                            "structured_content": {
                                "browser_channel": channel,
                                "clicked": True,
                                "success": True,
                                "matched_text": True,
                                "expected_text": expected,
                                "page_title": page_title,
                                "page_text_excerpt": page_text[:200] if isinstance(page_text, str) else None,
                                "skipped_click": True,
                            },
                            "content": [{"type": "text", "text": "Expected text already present before click retry."}],
                        }
                for selector in selector_values:
                    candidate = await browser.click(selector=str(selector))
                    candidate_structured = candidate.get("structured_content")
                    if not isinstance(candidate_structured, dict):
                        candidate_structured = {}
                    candidate_structured["browser_channel"] = channel
                    candidate_structured["selector_used"] = str(selector)
                    candidate["structured_content"] = candidate_structured
                    result = candidate
                    structured = candidate_structured
                    selector_used = str(selector)
                    if candidate_structured.get("clicked") is True:
                        break
                if result is None:
                    raise RuntimeError("No browser selector candidates were provided for click.")
                if expected_text:
                    page_text = None
                    page_title = None
                    matched = False
                    expected = str(expected_text)
                    page_title, page_text = await _read_browser_page(browser)
                    matched = _page_matches_expected(expected, page_title, page_text)

                    for _ in range(3):
                        if matched:
                            break
                        await asyncio.sleep(1)
                        page_title, page_text = await _read_browser_page(browser)
                        matched = _page_matches_expected(expected, page_title, page_text)
                        if matched:
                            break

                    if not matched and isinstance(fallback_url, str) and fallback_url.strip():
                        fallback_result = await browser.navigate(url=fallback_url)
                        fallback_structured = fallback_result.get("structured_content")
                        if not isinstance(fallback_structured, dict):
                            fallback_structured = {}
                        fallback_structured["browser_channel"] = channel
                        fallback_structured["fallback_navigation"] = True
                        fallback_result["structured_content"] = fallback_structured
                        result = fallback_result
                        structured = fallback_structured

                        for _ in range(3):
                            page_title, page_text = await _read_browser_page(browser)
                            matched = _page_matches_expected(expected, page_title, page_text)
                            if matched:
                                break
                            await asyncio.sleep(1)

                    structured.update(
                        {
                            "success": matched,
                            "expected_text": expected,
                            "matched_text": matched,
                            "page_title": page_title,
                            "page_text_excerpt": page_text[:200] if isinstance(page_text, str) else None,
                            "selector_used": selector_used,
                        }
                    )
                result["structured_content"] = structured
                return result
        except Exception as exc:
            last_error = exc
            continue

    if last_error is not None:
        raise last_error
    raise ValueError(f"Unsupported browser tool: {tool_name}")


async def _read_browser_page(browser: BrowserMCP) -> tuple[str | None, str | None]:
    page_title = None
    page_text = None

    title_eval = await browser.evaluate("() => document.title")
    title_candidate = _extract_browser_eval_text(title_eval)
    if isinstance(title_candidate, str) and title_candidate.strip():
        page_title = title_candidate

    evaluation = await browser.evaluate("() => document.body ? document.body.innerText : ''")
    candidate = _extract_browser_eval_text(evaluation)
    if isinstance(candidate, str) and candidate.strip():
        page_text = candidate

    return page_title, page_text


def _page_matches_expected(expected_text: str, page_title: str | None, page_text: str | None) -> bool:
    return (
        (isinstance(page_title, str) and expected_text in page_title)
        or (isinstance(page_text, str) and expected_text in page_text)
    )


def _extract_browser_eval_text(result: Any) -> str | None:
    if not isinstance(result, dict):
        return None

    structured = result.get("structured_content")
    if isinstance(structured, dict):
        candidate = structured.get("result")
        if isinstance(candidate, str):
            return candidate

    content = result.get("content")
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    stripped = text.strip()
                    if stripped.startswith('"') and stripped.endswith('"'):
                        return stripped.strip('"')
                    if stripped:
                        return stripped

    return None


async def _revise_tool_params_for_retry(
    state: VerifyFlowState,
    tool_name: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    from app.core.config import settings
    from app.core.llm import executor_llm

    verification_result = state["verification_result"] or {}
    retry_count = state["retry_count"]
    failure_indicators = verification_result.get("failure_indicators", [])

    try:
        revised = await executor_llm.chat_json(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You revise MCP tool parameters for a retry attempt. "
                        "Keep the same tool_name and only update tool_params when needed "
                        "to fix the failure indicators."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Task description: {state['current_task']['description']}\n"
                        f"Tool name: {tool_name}\n"
                        f"Current tool params: {params}\n\n"
                        f"Previous attempt failed. Judge analysis: {verification_result.get('judge_reasoning')}\n"
                        f"Failure indicators: {failure_indicators}\n"
                        f"Retry {retry_count} of {settings.max_retries}. Fix the specific issues identified."
                    ),
                },
            ],
            schema_hint='{"tool_params": {}}',
            temperature=0.1,
        )
    except Exception:
        return params

    revised_params = revised.get("tool_params")
    return revised_params if isinstance(revised_params, dict) else params


async def execute(state: VerifyFlowState, db: AsyncSession) -> VerifyFlowState:
    current_task = state["current_task"]
    if current_task is None:
        action_claim = {
            "tool_name": None,
            "params": {},
            "result": None,
            "claimed_success": False,
            "claimed_at": utcnow().isoformat(),
            "error": "No current task selected.",
        }
        return {**state, "action_claim": action_claim, "error": action_claim["error"]}

    tool_name = current_task["tool_name"]
    params = current_task.get("tool_params", {}) or {}
    if state["verification_result"] is not None and state["retry_count"] > 0:
        params = await _revise_tool_params_for_retry(state, tool_name, params)

    try:
        if tool_name.startswith("github."):
            result = await _call_github(tool_name, params)
        elif tool_name.startswith("filesystem."):
            result = await _call_filesystem(tool_name, params)
        elif tool_name.startswith("browser."):
            result = await _call_browser(tool_name, params)
        else:
            raise ValueError(f"Unsupported tool_name: {tool_name}")

        claimed_success = True
        if isinstance(result, dict):
            structured = result.get("structured_content")
            if isinstance(structured, dict):
                if isinstance(structured.get("success"), bool):
                    claimed_success = structured["success"]
                elif isinstance(structured.get("matched_text"), bool):
                    claimed_success = structured["matched_text"]
                elif isinstance(structured.get("clicked"), bool):
                    claimed_success = structured["clicked"]
                elif isinstance(structured.get("filled"), bool):
                    claimed_success = structured["filled"]
                elif result.get("is_error") is True:
                    claimed_success = False
            elif result.get("is_error") is True:
                claimed_success = False

        action_claim = {
            "tool_name": tool_name,
            "params": params,
            "result": result,
            "claimed_success": claimed_success,
            "claimed_at": utcnow().isoformat(),
        }
        if not claimed_success and isinstance(result, dict):
            error_details = result.get("error_details")
            if isinstance(error_details, dict):
                action_claim["error_details"] = error_details
            content = result.get("content", [])
            if isinstance(content, list) and content:
                first_item = content[0]
                if isinstance(first_item, dict):
                    text = first_item.get("text")
                    if isinstance(text, str) and text.strip():
                        action_claim["error"] = text.strip()
            if "error" not in action_claim and isinstance(result.get("error"), str):
                action_claim["error"] = result["error"]
            if "error_details" not in action_claim and action_claim.get("error"):
                action_claim["error_details"] = reliability.build_error_details(
                    action_claim["error"],
                    source=tool_name,
                )
    except Exception as exc:
        if isinstance(exc, MCPToolError):
            error_details = exc.to_error_details(source=tool_name)
        elif hasattr(exc, "to_error_details"):
            error_details = exc.to_error_details(source=tool_name)
        else:
            error_details = reliability.build_error_details(
                str(exc),
                source=tool_name,
                category="execution_error",
                retryable=False,
            )
        error_message = error_details.get("message") if isinstance(error_details, dict) else None
        action_claim = {
            "tool_name": tool_name,
            "params": params,
            "result": None,
            "claimed_success": False,
            "claimed_at": utcnow().isoformat(),
            "error": error_message if isinstance(error_message, str) and error_message.strip() else str(exc),
            "error_details": error_details,
        }

    task = await _load_task(db, current_task["id"])
    task.claimed_result = action_claim
    await db.commit()
    await db.refresh(task)

    updated_current_task = {
        **current_task,
        "tool_params": params,
        "claimed_result": task.claimed_result,
    }

    return {
        **state,
        "current_task": updated_current_task,
        "action_claim": action_claim,
        "error": action_claim.get("error"),
    }
