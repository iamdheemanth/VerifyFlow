from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.browser import BrowserMCP
from app.mcp.filesystem import FilesystemMCP
from app.mcp.github import GitHubMCP
from app.models.domain import Task, utcnow
from app.orchestrator.states import VerifyFlowState


async def _load_task(db: AsyncSession, task_id: str) -> Task:
    result = await db.execute(select(Task).where(Task.id == UUID(task_id)))
    return result.scalar_one()


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
    async with FilesystemMCP() as filesystem:
        if tool_name == "filesystem.write_file":
            return await filesystem.write_file(**params)
        if tool_name == "filesystem.read_file":
            return await filesystem.read_file(**params)
    raise ValueError(f"Unsupported filesystem tool: {tool_name}")


async def _call_browser(tool_name: str, params: dict[str, Any]) -> Any:
    async with BrowserMCP() as browser:
        if tool_name == "browser.navigate":
            return await browser.navigate(**params)
        if tool_name == "browser.fill":
            return await browser.fill(**params)
        if tool_name == "browser.click":
            return await browser.click(**params)
    raise ValueError(f"Unsupported browser tool: {tool_name}")


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

    try:
        if tool_name.startswith("github."):
            result = await _call_github(tool_name, params)
        elif tool_name.startswith("filesystem."):
            result = await _call_filesystem(tool_name, params)
        elif tool_name.startswith("browser."):
            result = await _call_browser(tool_name, params)
        else:
            raise ValueError(f"Unsupported tool_name: {tool_name}")

        action_claim = {
            "tool_name": tool_name,
            "params": params,
            "result": result,
            "claimed_success": True,
            "claimed_at": utcnow().isoformat(),
        }
    except Exception as exc:
        action_claim = {
            "tool_name": tool_name,
            "params": params,
            "result": None,
            "claimed_success": False,
            "claimed_at": utcnow().isoformat(),
            "error": str(exc),
        }

    task = await _load_task(db, current_task["id"])
    task.claimed_result = action_claim
    await db.commit()
    await db.refresh(task)

    updated_current_task = {
        **current_task,
        "claimed_result": task.claimed_result,
    }

    return {
        **state,
        "current_task": updated_current_task,
        "action_claim": action_claim,
        "error": action_claim.get("error"),
    }
