from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Load

from app.models.domain import Run
from app.routes._contracts import raise_api_error


def user_subject(current_user: dict[str, Any]) -> str:
    subject = current_user.get("sub")
    if isinstance(subject, str) and subject.strip():
        return subject.strip()

    email = current_user.get("email")
    if isinstance(email, str) and email.strip():
        return email.strip()

    raise_api_error(
        status.HTTP_401_UNAUTHORIZED,
        "invalid_authenticated_user",
        "Authenticated user is missing a stable subject.",
    )
    raise AssertionError("raise_api_error always raises")


def user_email(current_user: dict[str, Any]) -> str | None:
    email = current_user.get("email")
    if isinstance(email, str) and email.strip():
        return email.strip()
    return None


async def get_run_for_subject(
    db: AsyncSession,
    run_id: UUID,
    owner_subject: str,
    *,
    options: Iterable[Load] = (),
) -> Run:
    result = await db.execute(
        select(Run)
        .options(*options)
        .where(Run.id == run_id, Run.owner_subject == owner_subject)
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise_api_error(
            status.HTTP_404_NOT_FOUND,
            "run_not_found",
            "Run not found",
            details={"run_id": str(run_id)},
        )
    return run


async def get_run_for_user(
    db: AsyncSession,
    run_id: UUID,
    current_user: dict[str, Any],
    *,
    options: Iterable[Load] = (),
) -> Run:
    return await get_run_for_subject(
        db,
        run_id,
        user_subject(current_user),
        options=options,
    )
