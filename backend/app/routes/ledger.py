from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.domain import LedgerEntry, Task

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.get("/{run_id}")
async def get_ledger(run_id: UUID, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(
        select(LedgerEntry)
        .options(selectinload(LedgerEntry.task))
        .where(LedgerEntry.run_id == run_id)
        .order_by(LedgerEntry.created_at.asc())
    )
    entries = result.scalars().unique().all()
    return [
        {
            "id": str(entry.id),
            "run_id": str(entry.run_id),
            "task_id": str(entry.task_id),
            "attempt_id": str(entry.attempt_id) if entry.attempt_id else None,
            "task_description": entry.task.description if entry.task else "",
            "verification_method": entry.verification_method,
            "confidence": entry.confidence,
            "verified": entry.verified,
            "evidence": entry.evidence,
            "judge_reasoning": entry.judge_reasoning,
            "created_at": entry.created_at.isoformat(),
        }
        for entry in entries
    ]
