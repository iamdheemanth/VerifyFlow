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
from app.models.domain import (
    BenchmarkCase,
    BenchmarkSuite,
    Escalation,
    ModelPromptConfig,
    ReviewerDecision,
    Run,
    RunTelemetry,
    Task,
    TaskAttempt,
    utcnow,
)
from app.orchestrator.graph import run_graph
from app.schemas.run import (
    CreateRunRequest,
    ReliabilityOverviewSchema,
    RunSchema,
    RunSummarySchema,
    TaskSchema,
)

router = APIRouter(prefix="/runs", tags=["runs"])
logger = logging.getLogger(__name__)


def _to_run_summary(run: Run) -> RunSummarySchema:
    return RunSummarySchema(
        id=run.id,
        goal=run.goal,
        status=run.status,
        kind=run.kind,
        latest_confidence=run.latest_confidence,
        created_at=run.created_at,
        task_count=len(run.tasks),
    )


def _to_run_schema(run: Run) -> RunSchema:
    run.tasks.sort(key=lambda task: task.index)
    run.task_attempts.sort(key=lambda attempt: (attempt.task_id, attempt.attempt_index, attempt.created_at))
    return RunSchema(
        id=run.id,
        goal=run.goal,
        acceptance_criteria=run.acceptance_criteria,
        status=run.status,
        kind=run.kind,
        latest_confidence=run.latest_confidence,
        created_at=run.created_at,
        updated_at=run.updated_at,
        tasks=[TaskSchema.model_validate(task) for task in run.tasks],
        telemetry=run.telemetry,
        task_attempts=run.task_attempts,
        escalations=run.escalations,
        reviewer_decisions=run.reviewer_decisions,
        executor_config=run.executor_config,
        judge_config=run.judge_config,
        benchmark_suite=run.benchmark_suite,
        benchmark_case=run.benchmark_case,
    )


def _asyncpg_dsn() -> str | None:
    from app.db.session import _resolve_database_url

    database_url = _resolve_database_url()
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if database_url.startswith("postgresql://"):
        return database_url
    return None


async def _load_run_or_404(db: AsyncSession, run_id: UUID) -> Run:
    result = await db.execute(
        select(Run)
        .options(
            selectinload(Run.tasks),
            selectinload(Run.telemetry),
            selectinload(Run.task_attempts),
            selectinload(Run.escalations).selectinload(Escalation.reviewer_decisions),
            selectinload(Run.reviewer_decisions),
            selectinload(Run.executor_config),
            selectinload(Run.judge_config),
            selectinload(Run.benchmark_suite),
            selectinload(Run.benchmark_case),
        )
        .where(Run.id == run_id)
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


async def _run_graph_in_background(run_id: str) -> None:
    async with AsyncSessionLocal() as db:
        try:
            await run_graph(run_id, db)
        except Exception:
            logger.exception("Background graph execution failed for run %s", run_id)
            result = await db.execute(select(Run).where(Run.id == UUID(run_id)))
            run = result.scalar_one_or_none()
            if run is not None:
                run.status = "failed"
                run.updated_at = utcnow()
                await db.commit()


@router.post("", response_model=RunSummarySchema, status_code=status.HTTP_201_CREATED)
async def create_run(
    payload: CreateRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benchmark case not found")
        benchmark_suite_id = benchmark_case.suite_id

    run = Run(
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
async def get_reliability_overview(db: AsyncSession = Depends(get_db)) -> ReliabilityOverviewSchema:
    run_count = (await db.execute(select(func.count(Run.id)))).scalar_one()
    completed_runs = (await db.execute(select(func.count(Run.id)).where(Run.status == "completed"))).scalar_one()
    failed_runs = (await db.execute(select(func.count(Run.id)).where(Run.status == "failed"))).scalar_one()
    escalated_runs = (
        await db.execute(select(func.count(func.distinct(Escalation.run_id))))
    ).scalar_one()
    telemetry_rows = (await db.execute(select(RunTelemetry))).scalars().all()
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
async def delete_run(run_id: UUID, db: AsyncSession = Depends(get_db)) -> Response:
    run = await _load_run_or_404(db, run_id)
    await db.delete(run)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=list[RunSummarySchema])
async def list_runs(db: AsyncSession = Depends(get_db)) -> list[RunSummarySchema]:
    result = await db.execute(
        select(Run)
        .options(selectinload(Run.tasks))
        .order_by(Run.created_at.desc())
    )
    runs = result.scalars().unique().all()
    return [_to_run_summary(run) for run in runs]


@router.get("/{run_id}", response_model=RunSchema)
async def get_run(run_id: UUID, db: AsyncSession = Depends(get_db)) -> RunSchema:
    run = await _load_run_or_404(db, run_id)
    return _to_run_schema(run)


@router.delete("/{run_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(run_id: UUID, task_id: UUID, db: AsyncSession = Depends(get_db)) -> Response:
    run = await _load_run_or_404(db, run_id)
    task = next((task for task in run.tasks if task.id == task_id), None)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    await db.delete(task)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{run_id}/stream")
async def stream_run(run_id: UUID, request: Request) -> StreamingResponse:
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
                        run = await _load_run_or_404(db, run_id)
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
