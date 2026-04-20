from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.domain import LedgerEntry, Task
from app.routes._contracts import to_ledger_entry_schema
from app.schemas.run import LedgerEntrySchema

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.get("/{run_id}", response_model=list[LedgerEntrySchema])
async def get_ledger(run_id: UUID, db: AsyncSession = Depends(get_db)) -> list[LedgerEntrySchema]:
    result = await db.execute(
        select(LedgerEntry)
        .options(selectinload(LedgerEntry.task))
        .where(LedgerEntry.run_id == run_id)
        .order_by(LedgerEntry.created_at.asc())
    )
    entries = result.scalars().unique().all()
    return [to_ledger_entry_schema(entry, task_description=entry.task.description if entry.task else "") for entry in entries]
