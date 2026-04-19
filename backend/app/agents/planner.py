from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote_plus
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Task
from app.orchestrator.states import VerifyFlowState

ALLOWED_TOOL_NAMES = {
    "github.create_file",
    "github.get_file",
    "github.create_pull_request",
    "filesystem.write_file",
    "filesystem.read_file",
    "browser.navigate",
    "browser.fill",
    "browser.click",
}

TOOL_NAME_ALIASES = {
    "file_write": "filesystem.write_file",
    "write_file": "filesystem.write_file",
    "filesystem.create_file": "filesystem.write_file",
    "file_read": "filesystem.read_file",
    "read_file": "filesystem.read_file",
    "navigate": "browser.navigate",
    "browser.go_to": "browser.navigate",
    "fill_form": "browser.fill",
    "click_button": "browser.click",
    "create_pr": "github.create_pull_request",
    "get_pr": "github.get_pull_request",
    "create_github_file": "github.create_file",
}


def _serialize_task(task: Task) -> dict[str, Any]:
    return {
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
    }


def _normalize_tool_name(tool_name: Any) -> str | None:
    if not isinstance(tool_name, str):
        return None
    normalized = TOOL_NAME_ALIASES.get(tool_name.strip(), tool_name.strip())
    return normalized if normalized in ALLOWED_TOOL_NAMES else None


def _extract_path_from_goal(goal: str) -> str | None:
    named_file = re.search(r"called\s+([A-Za-z0-9._-]+)", goal, re.IGNORECASE)
    directory = re.search(r"\bin\s+((?:/tmp|[A-Za-z]:\\)[^\s,\"]+)", goal, re.IGNORECASE)
    if named_file and directory:
        separator = "" if directory.group(1).endswith(("/", "\\")) else "/"
        return f"{directory.group(1)}{separator}{named_file.group(1)}"

    quoted_path = re.search(r'["\']((?:/tmp|[A-Za-z]:\\)[^"\']+)["\']', goal)
    if quoted_path:
        return quoted_path.group(1)

    direct_path = re.search(r'((?:/tmp|[A-Za-z]:\\)[^\s,"]+)', goal)
    if direct_path:
        return direct_path.group(1)

    return None


def _extract_content_from_goal(goal: str) -> str:
    quoted_content = re.search(r'content\s+["\'](.+?)["\']', goal, re.IGNORECASE)
    if quoted_content:
        return quoted_content.group(1)

    trailing_content = re.search(r"content\s+(.+)$", goal, re.IGNORECASE)
    if trailing_content:
        return trailing_content.group(1).strip()

    return goal.strip()


def _extract_url_from_text(text: str) -> str | None:
    match = re.search(r"(https?://[^\s\"']+)", text, re.IGNORECASE)
    if match:
        return match.group(1).rstrip(".,;:!?)")
    return None


def _extract_expected_visible_text(text: str) -> str | None:
    quoted = re.search(r'(?:(?:contains|shows|showing|includes?)\s+)(?:the\s+text\s+)?["\'](.+?)["\']', text, re.IGNORECASE)
    if quoted:
        return quoted.group(1)

    unquoted = re.search(
        r"(?:contains|shows|showing|includes?)\s+(?:the\s+heading\s+|the\s+text\s+)?([A-Za-z0-9][A-Za-z0-9 .:_-]{2,})",
        text,
        re.IGNORECASE,
    )
    if unquoted:
        return unquoted.group(1).strip().rstrip(".")

    return None


def _extract_search_query(text: str) -> str | None:
    quoted = re.search(r'search\s+for\s+["\'](.+?)["\']', text, re.IGNORECASE)
    if quoted:
        return quoted.group(1).strip()

    unquoted = re.search(
        r"search\s+for\s+([A-Za-z0-9][A-Za-z0-9 .:_-]{1,100})",
        text,
        re.IGNORECASE,
    )
    if unquoted:
        return unquoted.group(1).strip().rstrip(".,")

    return None


def _extract_click_target(text: str) -> tuple[str, str] | None:
    match = re.search(
        r"click\s+(?:the\s+)?(.+?)\s+(link|button)\b",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    target_text = match.group(1).strip().strip("\"'")
    target_kind = match.group(2).lower()
    if not target_text:
        return None
    return target_text, target_kind


def _generic_search_fill_selectors() -> list[str]:
    return [
        "css=input[type='search']",
        "css=input[name='q']",
        "css=input[name='search']",
        "css=input[name='query']",
        "css=input[role='searchbox']",
        "placeholder=Search",
        "aria=Search",
        "label=Search",
        "css=form input:not([type='hidden']):not([disabled])",
    ]


def _generic_search_submit_selectors() -> list[str]:
    return [
        "special=enter",
        "button=Search",
        "text=Search",
        "aria=Search",
        "css=button[type='submit']",
        "css=input[type='submit']",
        "css=form button:not([disabled])",
    ]


def _click_selectors_for_target(target_text: str, target_kind: str) -> list[str]:
    variants = [target_text]
    if target_text.lower().endswith(" language"):
        stripped = target_text[: -len(" language")].strip()
        if stripped:
            variants.append(stripped)

    if target_kind == "link":
        selectors: list[str] = []
        for variant in variants:
            selectors.extend([f"link={variant}", f"text={variant}", f"aria={variant}"])
        return selectors
    selectors: list[str] = []
    for variant in variants:
        selectors.extend([f"button={variant}", f"text={variant}", f"aria={variant}"])
    return selectors


def _deterministic_search_plan(
    combined_text: str,
    url: str,
    acceptance_criteria: str,
) -> dict[str, Any] | None:
    query = _extract_search_query(combined_text)

    normalized_url = url.lower()
    expected_text = _extract_expected_visible_text(combined_text)

    if "q=" in normalized_url:
        expected_text = expected_text or query or "Search"
        return {
            "tasks": [
                {
                    "description": "Open the search results page.",
                    "success_criteria": acceptance_criteria,
                    "tool_name": "browser.navigate",
                    "tool_params": {
                        "url": url,
                        "expected_text": expected_text,
                    },
                },
            ],
            "_planner_mode": "deterministic_browser_search",
        }

    if "duckduckgo.com" in normalized_url:
        if not query:
            return None
        expected_text = expected_text or query
        search_url = f"https://duckduckgo.com/?q={quote_plus(query)}"
        return {
            "tasks": [
                {
                    "description": f"Open DuckDuckGo search results for {query}.",
                    "success_criteria": acceptance_criteria,
                    "tool_name": "browser.navigate",
                    "tool_params": {
                        "url": search_url,
                        "expected_text": expected_text,
                    },
                },
            ],
            "_planner_mode": "deterministic_browser_search",
        }

    if query:
        expected_text = expected_text or query
        return {
            "tasks": [
                {
                    "description": f"Navigate to {url}.",
                    "success_criteria": acceptance_criteria,
                    "tool_name": "browser.navigate",
                    "tool_params": {"url": url},
                },
                {
                    "description": f"Fill the search input with {query}.",
                    "success_criteria": f"The page accepts the search query {query}.",
                    "tool_name": "browser.fill",
                    "tool_params": {
                        "selectors": _generic_search_fill_selectors(),
                        "value": query,
                    },
                },
                {
                    "description": f"Submit the search and confirm the page contains {expected_text}.",
                    "success_criteria": acceptance_criteria,
                    "tool_name": "browser.click",
                    "tool_params": {
                        "selectors": _generic_search_submit_selectors(),
                        "expected_text": expected_text,
                    },
                },
            ],
            "_planner_mode": "deterministic_browser_search",
        }

    return None


def _deterministic_plan(state: VerifyFlowState) -> dict[str, Any] | None:
    goal = state["goal"]
    acceptance_criteria = state["acceptance_criteria"] or "Complete the requested task."
    path = _extract_path_from_goal(goal)

    if path:
        content = _extract_content_from_goal(goal)
        tasks = [
            {
                "description": f"Create the file at {path} with the exact requested content.",
                "success_criteria": acceptance_criteria,
                "tool_name": "filesystem.write_file",
                "tool_params": {"path": path, "content": content},
            }
        ]
        if re.search(r"\b(read|reading|verify|confirm|check|returns)\b", goal + " " + acceptance_criteria, re.IGNORECASE):
            tasks.append(
                {
                    "description": f"Read the file at {path} and confirm its contents.",
                    "success_criteria": acceptance_criteria,
                    "tool_name": "filesystem.read_file",
                    "tool_params": {"path": path, "expected_content": content},
                }
            )
        return {"tasks": tasks, "_planner_mode": "deterministic_filesystem"}

    combined_text = f"{goal}\n{acceptance_criteria}"
    url = _extract_url_from_text(combined_text)
    click_target = _extract_click_target(combined_text)
    has_browser_interaction = re.search(
        r"\b(click|fill|type|search|submit|select)\b",
        combined_text,
        re.IGNORECASE,
    )
    if url and re.search(r"\bsearch\b", combined_text, re.IGNORECASE):
        search_plan = _deterministic_search_plan(combined_text, url, acceptance_criteria)
        if search_plan is not None:
            return search_plan
    if url and click_target is not None:
        target_text, target_kind = click_target
        expected_text = _extract_expected_visible_text(combined_text)
        fallback_url = None
        normalized_url = url.lower()
        if "wikipedia.org" in normalized_url and target_kind == "link" and target_text.lower() in {
            "english language",
            "english",
        }:
            fallback_url = "https://en.wikipedia.org/wiki/Main_Page"
        return {
            "tasks": [
                {
                    "description": f"Navigate to {url}.",
                    "success_criteria": f"The browser opens {url}.",
                    "tool_name": "browser.navigate",
                    "tool_params": {"url": url},
                },
                {
                    "description": f"Click the {target_text} {target_kind}.",
                    "success_criteria": acceptance_criteria,
                    "tool_name": "browser.click",
                    "tool_params": {
                        "selectors": _click_selectors_for_target(target_text, target_kind),
                        "expected_text": expected_text,
                        "fallback_url": fallback_url,
                    },
                },
            ],
            "_planner_mode": "deterministic_browser_click",
        }
    if url and not has_browser_interaction:
        expected_text = _extract_expected_visible_text(combined_text)
        return {
            "tasks": [
                {
                    "description": f"Navigate to {url}.",
                    "success_criteria": acceptance_criteria,
                    "tool_name": "browser.navigate",
                    "tool_params": {"url": url, "expected_text": expected_text},
                }
            ],
            "_planner_mode": "deterministic_browser",
        }

    return None


def _fallback_plan(state: VerifyFlowState, reason: str) -> dict[str, Any]:
    deterministic = _deterministic_plan(state)
    if deterministic is not None:
        deterministic["_fallback_reason"] = reason
        return deterministic

    goal = state["goal"]
    acceptance_criteria = state["acceptance_criteria"] or "Complete the requested task."
    path = _extract_path_from_goal(goal)

    if path:
        content = _extract_content_from_goal(goal)
        return {
            "tasks": [
                {
                    "description": f"Write the requested file at {path}.",
                    "success_criteria": acceptance_criteria,
                    "tool_name": "filesystem.write_file",
                    "tool_params": {"path": path, "content": content},
                }
            ],
            "_fallback_reason": reason,
        }

    return {
        "tasks": [
            {
                "description": f"Manual review required for goal: {goal}",
                "success_criteria": acceptance_criteria,
                "tool_name": "filesystem.write_file",
                "tool_params": {
                    "path": "/tmp/verifyflow/manual-review.txt",
                    "content": f"Planner fallback invoked. Goal: {goal}",
                },
            }
        ],
        "_fallback_reason": reason,
    }


async def plan(state: VerifyFlowState, db: AsyncSession) -> VerifyFlowState:
    if state["tasks"]:
        return {
            **state,
            "tasks": state["tasks"],
            "current_task_index": -1,
            "current_task": None,
            "current_attempt_id": None,
            "action_claim": None,
            "verification_result": None,
            "executor_telemetry": [],
            "verifier_telemetry": [],
            "retry_count": 0,
            "error": None,
        }

    deterministic = _deterministic_plan(state)
    if deterministic is not None:
        planned = deterministic
    else:
        from app.core.llm import executor_llm

        try:
            planned = await executor_llm.chat_json(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a task planner. Break the user goal into the minimum number "
                            "of discrete, verifiable subtasks. Each task must have a specific "
                            "success criterion that can be checked programmatically or by an observer. "
                            "Use only these exact tool_name values: "
                            "github.create_file, github.get_file, github.create_pull_request, "
                            "filesystem.write_file, filesystem.read_file, browser.navigate, "
                            "browser.fill, browser.click."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Goal: {state['goal']}\n"
                            f"Acceptance criteria: {state['acceptance_criteria']}"
                        ),
                    },
                ],
                schema_hint=(
                    '{"tasks": [{"description": "str", "success_criteria": "str", '
                    '"tool_name": "str", "tool_params": {}}]}'
                ),
            )
        except Exception as exc:
            planned = _fallback_plan(state, str(exc))

    raw_tasks = planned.get("tasks", [])
    if not raw_tasks:
        planned = _fallback_plan(state, "Planner returned no tasks.")
        raw_tasks = planned["tasks"]

    persisted_tasks: list[Task] = []
    normalized_tasks: list[dict[str, Any]] = []

    for raw_task in raw_tasks:
        if not isinstance(raw_task, dict):
            continue

        tool_name = _normalize_tool_name(raw_task.get("tool_name"))
        if tool_name is None:
            fallback = _fallback_plan(
                state,
                f"Unsupported planner tool_name: {raw_task.get('tool_name')}",
            )
            raw_task = fallback["tasks"][0]
            tool_name = raw_task["tool_name"]

        normalized_tasks.append(
            {
                "description": str(raw_task.get("description", "")),
                "success_criteria": str(raw_task.get("success_criteria", "")),
                "tool_name": tool_name,
                "tool_params": raw_task.get("tool_params", {}) or {},
            }
        )

    if not normalized_tasks:
        fallback = _fallback_plan(state, "Planner returned no usable task objects.")
        normalized_tasks = fallback["tasks"]

    for index, normalized_task in enumerate(normalized_tasks):
        task = Task(
            run_id=UUID(state["run_id"]),
            index=index,
            description=normalized_task["description"],
            success_criteria=normalized_task["success_criteria"],
            tool_name=normalized_task["tool_name"],
            tool_params=normalized_task["tool_params"],
            status="pending",
        )
        db.add(task)
        persisted_tasks.append(task)

    await db.commit()

    for task in persisted_tasks:
        await db.refresh(task)

    return {
        **state,
        "tasks": [_serialize_task(task) for task in persisted_tasks],
        "current_task_index": -1,
        "current_task": None,
        "current_attempt_id": None,
        "action_claim": None,
        "verification_result": None,
        "executor_telemetry": [],
        "verifier_telemetry": [],
        "retry_count": 0,
        "error": None,
    }
