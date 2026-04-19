from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.domain import Escalation
from app.schemas.run import EscalationSchema, ReviewerDecisionRequest, ReviewerDecisionSchema
from app.services import reliability

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/queue", response_model=list[EscalationSchema])
async def list_escalation_queue(db: AsyncSession = Depends(get_db)) -> list[EscalationSchema]:
    result = await db.execute(
        select(Escalation)
        .options(selectinload(Escalation.reviewer_decisions))
        .order_by(Escalation.created_at.desc())
    )
    return result.scalars().unique().all()


@router.post("/escalations/{escalation_id}/decision", response_model=ReviewerDecisionSchema)
async def submit_reviewer_decision(
    escalation_id: UUID,
    payload: ReviewerDecisionRequest,
    db: AsyncSession = Depends(get_db),
) -> ReviewerDecisionSchema:
    if payload.decision not in {"approve", "reject", "send_back"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reviewer decision")

    result = await db.execute(
        select(Escalation)
        .options(selectinload(Escalation.reviewer_decisions))
        .where(Escalation.id == escalation_id)
    )
    escalation = result.scalar_one_or_none()
    if escalation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found")

    decision = await reliability.record_reviewer_decision(
        db,
        escalation=escalation,
        decision=payload.decision,
        notes=payload.notes,
        reviewer_name=payload.reviewer_name,
    )
    return decision
