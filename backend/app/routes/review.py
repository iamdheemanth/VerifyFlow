from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import verify_token
from app.db.session import get_db
from app.models.domain import Escalation, Run
from app.routes.authorization import user_subject
from app.routes._contracts import raise_api_error, to_escalation_schema, to_reviewer_decision_schema
from app.schemas.run import EscalationSchema, ReviewerDecisionRequest, ReviewerDecisionSchema
from app.services import reliability, run_queue

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/queue", response_model=list[EscalationSchema])
async def list_escalation_queue(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
) -> list[EscalationSchema]:
    owner = user_subject(current_user)
    result = await db.execute(
        select(Escalation)
        .options(selectinload(Escalation.reviewer_decisions))
        .join(Run, Escalation.run_id == Run.id)
        .where(Escalation.status == "pending_review")
        .where(Run.owner_subject == owner)
        .order_by(Escalation.created_at.desc())
    )
    escalations = result.scalars().unique().all()
    payload: list[EscalationSchema] = []
    for escalation in escalations:
        task = await reliability._load_task(db, escalation.task_id)
        run = await reliability._load_run(db, escalation.run_id)
        payload.append(to_escalation_schema(escalation, task_status=task.status, run_status=run.status))
    return payload


@router.post("/escalations/{escalation_id}/decision", response_model=ReviewerDecisionSchema)
async def submit_reviewer_decision(
    escalation_id: UUID,
    payload: ReviewerDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
) -> ReviewerDecisionSchema:
    if payload.decision not in {"approve", "reject", "send_back"}:
        raise_api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_reviewer_decision",
            "Invalid reviewer decision",
            details={"decision": payload.decision},
        )
    if not payload.reviewer_key.strip():
        raise_api_error(status.HTTP_400_BAD_REQUEST, "reviewer_key_required", "Reviewer key is required")

    result = await db.execute(
        select(Escalation)
        .options(selectinload(Escalation.reviewer_decisions))
        .join(Run, Escalation.run_id == Run.id)
        .where(Escalation.id == escalation_id)
        .where(Run.owner_subject == user_subject(current_user))
    )
    escalation = result.scalar_one_or_none()
    if escalation is None:
        raise_api_error(
            status.HTTP_404_NOT_FOUND,
            "escalation_not_found",
            "Escalation not found",
            details={"escalation_id": str(escalation_id)},
        )

    try:
        decision = await reliability.record_reviewer_decision(
            db,
            escalation=escalation,
            decision=payload.decision,
            notes=payload.notes,
            reviewer_key=payload.reviewer_key,
            reviewer_display_name=payload.reviewer_display_name,
        )
    except ValueError as exc:
        message = str(exc)
        if "already been resolved" in message:
            raise_api_error(
                status.HTTP_409_CONFLICT,
                "escalation_already_resolved",
                "Escalation has already been resolved",
                details={"escalation_id": str(escalation_id), "status": escalation.status},
            )
        raise
    await db.refresh(escalation)
    task = await reliability._load_task(db, escalation.task_id)
    run = await reliability._load_run(db, escalation.run_id)

    reprocess_requested = payload.decision == "send_back"
    if reprocess_requested:
        run = await run_queue.enqueue_run(db, escalation.run_id)
        await db.refresh(task)

    return to_reviewer_decision_schema(
        decision,
        escalation_status=escalation.status,
        task_status=task.status,
        run_status=run.status,
        reprocess_requested=reprocess_requested,
    )
