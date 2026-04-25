from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("LLM_BASE_URL", "https://openrouter.ai/api/v1")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_MODEL", "executor-model")
os.environ.setdefault("LLM_JUDGE_MODEL", "judge-model")
os.environ.setdefault("GITHUB_TOKEN", "test-token")
os.environ.setdefault("GITHUB_OWNER", "test-owner")
os.environ.setdefault("MAX_RETRIES", "3")
os.environ.setdefault("VERIFICATION_CONFIDENCE_THRESHOLD", "0.75")

from app.db.session import Base
from app.models.domain import Escalation, Run, Task
from app.routes import review as review_module
from app.schemas.run import ReviewerDecisionRequest
from app.services import reliability


async def _make_session() -> tuple[AsyncSession, any]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session = session_factory()
    return session, engine


async def _seed_escalated_run(session: AsyncSession) -> tuple[Run, Task, Escalation]:
    run_id = uuid4()
    task_id = uuid4()
    run = Run(
        id=run_id,
        owner_subject="test-user",
        owner_email="test@example.com",
        goal="Escalated review flow",
        acceptance_criteria="Reviewer decision updates state coherently",
        status="needs_review",
    )
    task = Task(
        id=task_id,
        run_id=run_id,
        index=0,
        description="Escalated task",
        success_criteria="Task is resolved through review",
        tool_name="browser.click",
        tool_params={"selector": "text=English"},
        status="escalated",
        retry_count=3,
        claimed_result={"claimed_success": False, "error": "Element not found"},
    )
    escalation = Escalation(
        run_id=run_id,
        task_id=task_id,
        status="pending_review",
        failure_reason="Element not found",
        evidence_bundle={"task": "Escalated task"},
    )
    session.add(run)
    session.add(task)
    session.add(escalation)
    await session.commit()
    await session.refresh(run)
    await session.refresh(task)
    await session.refresh(escalation)
    return run, task, escalation


@pytest.mark.asyncio
async def test_reviewer_approve_marks_task_verified_and_run_completed():
    session, engine = await _make_session()
    try:
        run, task, escalation = await _seed_escalated_run(session)

        decision = await reliability.record_reviewer_decision(
            session,
            escalation=escalation,
            decision="approve",
            notes="I confirmed the task manually.",
            reviewer_key="alice",
            reviewer_display_name="Alice Reviewer",
        )

        await session.refresh(run)
        await session.refresh(task)
        await session.refresh(escalation)

        assert decision.reviewer_key == "alice"
        assert decision.reviewer_display_name == "Alice Reviewer"
        assert decision.reviewer_name == "Alice Reviewer"
        assert escalation.status == "approved"
        assert task.status == "verified"
        assert run.status == "completed"
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_reviewer_reject_marks_task_failed_and_run_failed():
    session, engine = await _make_session()
    try:
        run, task, escalation = await _seed_escalated_run(session)

        decision = await reliability.record_reviewer_decision(
            session,
            escalation=escalation,
            decision="reject",
            notes="The evidence does not support approval.",
            reviewer_key="bob",
            reviewer_display_name=None,
        )

        await session.refresh(run)
        await session.refresh(task)
        await session.refresh(escalation)

        assert decision.reviewer_key == "bob"
        assert decision.reviewer_name == "bob"
        assert escalation.status == "rejected"
        assert task.status == "failed"
        assert run.status == "failed"
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_send_back_resets_task_and_schedules_reprocessing():
    session, engine = await _make_session()
    try:
        run, task, escalation = await _seed_escalated_run(session)

        response = await review_module.submit_reviewer_decision(
            escalation_id=escalation.id,
            payload=ReviewerDecisionRequest(
                decision="send_back",
                notes="Try again with a different selector.",
                reviewer_key="carol",
                reviewer_display_name="Carol QA",
            ),
            db=session,
            current_user={"sub": "test-user", "email": "test@example.com"},
        )

        await session.refresh(run)
        await session.refresh(task)
        await session.refresh(escalation)

        assert escalation.status == "sent_back"
        assert task.status == "pending"
        assert task.retry_count == 0
        assert task.claimed_result is None
        assert run.status == "queued"
        assert run.queued_at is not None
        assert response.reviewer_key == "carol"
        assert response.reviewer_display_name == "Carol QA"
        assert response.reprocess_requested is True
        assert response.task_status == "pending"
        assert response.run_status == "queued"
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_resolved_escalation_rejects_additional_service_decisions():
    session, engine = await _make_session()
    try:
        _run, _task, escalation = await _seed_escalated_run(session)

        await reliability.record_reviewer_decision(
            session,
            escalation=escalation,
            decision="approve",
            notes="Initial final decision.",
            reviewer_key="alice",
            reviewer_display_name="Alice Reviewer",
        )
        await session.refresh(escalation)

        with pytest.raises(ValueError, match="already been resolved"):
            await reliability.record_reviewer_decision(
                session,
                escalation=escalation,
                decision="reject",
                notes="Late conflicting decision.",
                reviewer_key="bob",
                reviewer_display_name="Bob Reviewer",
            )
    finally:
        await session.close()
        await engine.dispose()
