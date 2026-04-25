from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID

import asyncpg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal, get_db
from app.core.auth import verify_token
from app.models.domain import (
    BenchmarkCase,
    Escalation,
    LedgerEntry,
    ModelPromptConfig,
    RunTelemetry,
    Run,
)
from app.orchestrator.graph import run_graph
from app.routes.authorization import get_run_for_subject, get_run_for_user, user_email, user_subject
from app.routes._contracts import (
    build_task_evidence,
    build_run_inspection,
    raise_api_error,
    to_run_schema,
    to_run_summary,
)
from app.schemas.run import (
    CreateRunRequest,
    ReliabilityOverviewSchema,
    RunInspectionSchema,
    RunSchema,
    RunSummarySchema,
    TaskEvidenceSchema,
)

router = APIRouter(prefix="/runs", tags=["runs"])
logger = logging.getLogger(__name__)

RUN_LOAD_OPTIONS = (
    selectinload(Run.tasks),
    selectinload(Run.telemetry),
    selectinload(Run.task_attempts),
    selectinload(Run.ledger_entries).selectinload(LedgerEntry.task),
    selectinload(Run.escalations).selectinload(Escalation.reviewer_decisions),
    selectinload(Run.reviewer_decisions),
    selectinload(Run.executor_config),
    selectinload(Run.judge_config),
    selectinload(Run.benchmark_suite),
    selectinload(Run.benchmark_case),
)


def _asyncpg_dsn() -> str | None:
    from app.db.session import _resolve_database_url

    database_url = _resolve_database_url()
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if database_url.startswith("postgresql://"):
        return database_url
    return None


async def _load_run_for_user_or_404(db: AsyncSession, run_id: UUID, current_user: dict) -> Run:
    return await get_run_for_user(db, run_id, current_user, options=RUN_LOAD_OPTIONS)


async def _run_graph_in_background(run_id: str) -> None:
    async with AsyncSessionLocal() as db:
        try:
            await run_graph(run_id, db)
        except Exception:
            logger.exception("Background graph execution failed for run %s", run_id)


@router.post("", response_model=RunSummarySchema, status_code=status.HTTP_201_CREATED)
async def create_run(
    payload: CreateRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
) -> RunSummarySchema:
    kind = "benchmark" if payload.benchmark_case_id else "standard"
    benchmark_case = None
    benchmark_suite_id = None
    if payload.benchmark_case_id is not None:
        benchmark_case_result = await db.execute(
            select(BenchmarkCase).where(BenchmarkCase.id == payload.benchmark_case_id)
        )
        benchmark_case = benchmark_case_result.scalar_one_or_none()
        if benchmark_case is None:
            raise_api_error(
                status.HTTP_404_NOT_FOUND,
                "benchmark_case_not_found",
                "Benchmark case not found",
                details={"benchmark_case_id": str(payload.benchmark_case_id)},
            )
        benchmark_suite_id = benchmark_case.suite_id

    run = Run(
        owner_subject=user_subject(current_user),
        owner_email=user_email(current_user),
        goal=payload.goal,
        acceptance_criteria=payload.acceptance_criteria,
        status="pending",
        kind=kind,
        executor_config_id=payload.executor_config_id,
        judge_config_id=payload.judge_config_id,
        benchmark_case_id=payload.benchmark_case_id,
        benchmark_suite_id=benchmark_suite_id,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    background_tasks.add_task(_run_graph_in_background, str(run.id))
    return RunSummarySchema(
        id=run.id,
        goal=run.goal,
        status=run.status,
        kind=run.kind,
        latest_confidence=run.latest_confidence,
        created_at=run.created_at,
        task_count=0,
    )


@router.get("/overview", response_model=ReliabilityOverviewSchema)
async def get_reliability_overview(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
) -> ReliabilityOverviewSchema:
    owner = user_subject(current_user)
    run_count = (await db.execute(select(func.count(Run.id)).where(Run.owner_subject == owner))).scalar_one()
    completed_runs = (
        await db.execute(select(func.count(Run.id)).where(Run.owner_subject == owner, Run.status == "completed"))
    ).scalar_one()
    failed_runs = (
        await db.execute(select(func.count(Run.id)).where(Run.owner_subject == owner, Run.status == "failed"))
    ).scalar_one()
    escalated_runs = (
        await db.execute(
            select(func.count(func.distinct(Escalation.run_id)))
            .join(Run, Escalation.run_id == Run.id)
            .where(Run.owner_subject == owner)
        )
    ).scalar_one()
    telemetry_rows = (
        await db.execute(
            select(RunTelemetry)
            .join(Run, RunTelemetry.run_id == Run.id)
            .where(Run.owner_subject == owner)
        )
    ).scalars().all()
    average_confidence = (
        sum(item.average_confidence for item in telemetry_rows) / len(telemetry_rows)
        if telemetry_rows
        else 0.0
    )
    total_estimated_cost = sum(item.total_estimated_cost_usd for item in telemetry_rows)
    total_tokens = sum(item.total_token_total for item in telemetry_rows)
    return ReliabilityOverviewSchema(
        total_runs=run_count,
        completed_runs=completed_runs,
        failed_runs=failed_runs,
        escalated_runs=escalated_runs,
        average_confidence=average_confidence,
        total_estimated_cost_usd=total_estimated_cost,
        total_tokens=total_tokens,
    )


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
) -> Response:
    run = await _load_run_for_user_or_404(db, run_id, current_user)
    await db.delete(run)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=list[RunSummarySchema])
async def list_runs(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
) -> list[RunSummarySchema]:
    result = await db.execute(
        select(Run)
        .options(selectinload(Run.tasks))
        .where(Run.owner_subject == user_subject(current_user))
        .order_by(Run.created_at.desc())
    )
    runs = result.scalars().unique().all()
    return [to_run_summary(run) for run in runs]


@router.get("/{run_id}", response_model=RunSchema)
async def get_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
) -> RunSchema:
    run = await _load_run_for_user_or_404(db, run_id, current_user)
    return to_run_schema(run)


@router.get("/{run_id}/inspection", response_model=RunInspectionSchema)
async def inspect_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
) -> RunInspectionSchema:
    run = await _load_run_for_user_or_404(db, run_id, current_user)
    return build_run_inspection(run)


@router.get("/{run_id}/tasks/{task_id}/evidence", response_model=TaskEvidenceSchema)
async def get_task_evidence(
    run_id: UUID,
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
) -> TaskEvidenceSchema:
    run = await _load_run_for_user_or_404(db, run_id, current_user)
    task = next((item for item in run.tasks if item.id == task_id), None)
    if task is None:
        raise_api_error(
            status.HTTP_404_NOT_FOUND,
            "task_not_found",
            "Task not found",
            details={"run_id": str(run_id), "task_id": str(task_id)},
        )
    return build_task_evidence(run, task)


@router.delete("/{run_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    run_id: UUID,
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
) -> Response:
    run = await _load_run_for_user_or_404(db, run_id, current_user)
    task = next((task for task in run.tasks if task.id == task_id), None)
    if task is None:
        raise_api_error(
            status.HTTP_404_NOT_FOUND,
            "task_not_found",
            "Task not found",
            details={"run_id": str(run_id), "task_id": str(task_id)},
        )
    await db.delete(task)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{run_id}/stream")
async def stream_run(
    run_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(verify_token),
) -> StreamingResponse:
    owner = user_subject(current_user)
    await get_run_for_subject(db, run_id, owner, options=(selectinload(Run.tasks),))

    async def event_generator():
        queue: asyncio.Queue[dict] = asyncio.Queue()
        listen_task: asyncio.Task | None = None
        stop_event = asyncio.Event()
        dsn = _asyncpg_dsn()

        async def listen_for_escalations():
            try:
                connection = await asyncpg.connect(dsn)  # type: ignore[arg-type]
            except Exception:
                logger.warning("Run stream escalation listener unavailable for %s", run_id, exc_info=True)
                return

            def _listener(_conn, _pid, _channel, payload: str):
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    return
                if data.get("run_id") == str(run_id):
                    queue.put_nowait(data)

            await connection.add_listener("task_escalated", _listener)
            try:
                await stop_event.wait()
            finally:
                await connection.remove_listener("task_escalated", _listener)
                await connection.close()

        if dsn is not None:
            listen_task = asyncio.create_task(listen_for_escalations())

        last_statuses: dict[str, str] = {}
        run_complete_sent = False

        try:
            while True:
                if await request.is_disconnected():
                    break

                async with AsyncSessionLocal() as db:
                    try:
                        run = await get_run_for_subject(
                            db,
                            run_id,
                            owner,
                            options=(selectinload(Run.tasks),),
                        )
                    except HTTPException:
                        yield "data: " + json.dumps({"type": "error", "message": "Run not found"}) + "\n\n"
                        break
                    except Exception:
                        logger.warning("Run stream database poll failed for %s", run_id, exc_info=True)
                        yield "data: " + json.dumps(
                            {"type": "error", "message": "Database connection unavailable"}
                        ) + "\n\n"
                        break

                    for task in sorted(run.tasks, key=lambda item: item.index):
                        task_id = str(task.id)
                        if last_statuses.get(task_id) != task.status:
                            last_statuses[task_id] = task.status
                            yield "data: " + json.dumps(
                                {
                                    "type": "task_update",
                                    "task_id": task_id,
                                    "status": task.status,
                                }
                            ) + "\n\n"

                    if run.status in {"completed", "failed"} and not run_complete_sent:
                        run_complete_sent = True
                        yield "data: " + json.dumps(
                            {"type": "run_complete", "run_id": str(run.id), "status": run.status}
                        ) + "\n\n"
                        break

                while not queue.empty():
                    event = await queue.get()
                    event.setdefault("type", "escalation")
                    yield "data: " + json.dumps(event) + "\n\n"

                await asyncio.sleep(1)
        finally:
            stop_event.set()
            if listen_task is not None:
                await asyncio.gather(listen_task, return_exceptions=True)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
