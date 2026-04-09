from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CreateRunRequest(BaseModel):
    goal: str
    acceptance_criteria: str | None = None


class TaskSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    index: int
    description: str
    success_criteria: str
    tool_name: str
    tool_params: dict[str, Any]
    status: str
    claimed_result: dict[str, Any] | None
    retry_count: int
    created_at: datetime


class RunSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    goal: str
    acceptance_criteria: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    tasks: list[TaskSchema]


class RunSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    goal: str
    status: str
    created_at: datetime
    task_count: int
