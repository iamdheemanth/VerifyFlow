from __future__ import annotations

import os
from typing import Any

from mcp import StdioServerParameters

from app.core.config import settings
from app.mcp import BaseMCPClient, extract_text, normalize_tool_result


class GitHubMCP(BaseMCPClient):
    def __init__(self):
        env = os.environ.copy()
        env["GITHUB_PERSONAL_ACCESS_TOKEN"] = settings.github_token
        super().__init__(
            StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                env=env,
            )
        )
        self.owner = settings.github_owner

    async def create_file(self, repo: str, path: str, content: str, message: str) -> dict[str, Any]:
        result = await self._call_tool(
            "create_or_update_file",
            {
                "owner": self.owner,
                "repo": repo,
                "path": path,
                "content": content,
                "message": message,
                "branch": "main",
            },
        )
        return normalize_tool_result(result)

    async def get_file(self, repo: str, path: str) -> dict[str, Any] | None:
        result = await self._call_tool(
            "get_file_contents",
            {
                "owner": self.owner,
                "repo": repo,
                "path": path,
            },
        )
        if result.isError:
            return None
        return normalize_tool_result(result)

    async def create_pull_request(
        self,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> dict[str, Any]:
        result = await self._call_tool(
            "create_pull_request",
            {
                "owner": self.owner,
                "repo": repo,
                "title": title,
                "body": body,
                "head": head,
                "base": base,
            },
        )
        return normalize_tool_result(result)

    async def get_pull_request(self, repo: str, pr_number: int) -> dict[str, Any] | None:
        result = await self._call_tool(
            "get_pull_request",
            {
                "owner": self.owner,
                "repo": repo,
                "pull_number": pr_number,
            },
        )
        if result.isError:
            return None
        return normalize_tool_result(result)

    async def list_commits(self, repo: str, since_sha: str) -> list[dict[str, Any]]:
        result = await self._call_tool(
            "list_commits",
            {
                "owner": self.owner,
                "repo": repo,
                "sha": since_sha,
            },
        )
        if result.isError:
            return []

        if result.structuredContent and isinstance(result.structuredContent, dict):
            commits = result.structuredContent.get("commits")
            if isinstance(commits, list):
                return [commit for commit in commits if isinstance(commit, dict)]

        text = extract_text(result)
        if not text:
            return []
        return [{"text": text}]
