from __future__ import annotations

import asyncio
import json
from uuid import UUID

import asyncpg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal, get_db
from app.models.domain import Run
from app.orchestrator.graph import run_graph
from app.schemas.run import CreateRunRequest, RunSchema, RunSummarySchema, TaskSchema

router = APIRouter(prefix="/runs", tags=["runs"])


def _to_run_summary(run: Run) -> RunSummarySchema:
    return RunSummarySchema(
        id=run.id,
        goal=run.goal,
        status=run.status,
        created_at=run.created_at,
        task_count=len(run.tasks),
    )


def _to_run_schema(run: Run) -> RunSchema:
    return RunSchema(
        id=run.id,
        goal=run.goal,
        acceptance_criteria=run.acceptance_criteria,
        status=run.status,
        created_at=run.created_at,
        updated_at=run.updated_at,
        tasks=[TaskSchema.model_validate(task) for task in run.tasks],
    )


def _asyncpg_dsn() -> str | None:
    from app.db.session import _resolve_database_url

    database_url = _resolve_database_url()
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if database_url.startswith("postgresql://"):
        return database_url
    return None


async def _run_graph_in_background(run_id: str) -> None:
    async with AsyncSessionLocal() as db:
        await run_graph(run_id, db)


@router.post("", response_model=RunSummarySchema, status_code=status.HTTP_201_CREATED)
async def create_run(
    payload: CreateRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> RunSummarySchema:
    run = Run(
        goal=payload.goal,
        acceptance_criteria=payload.acceptance_criteria,
        status="pending",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    background_tasks.add_task(_run_graph_in_background, str(run.id))
    return RunSummarySchema(
        id=run.id,
        goal=run.goal,
        status=run.status,
        created_at=run.created_at,
        task_count=0,
    )


@router.get("", response_model=list[RunSummarySchema])
async def list_runs(db: AsyncSession = Depends(get_db)) -> list[RunSummarySchema]:
    result = await db.execute(
        select(Run).options(selectinload(Run.tasks)).order_by(Run.created_at.desc())
    )
    runs = result.scalars().unique().all()
    return [_to_run_summary(run) for run in runs]


@router.get("/{run_id}", response_model=RunSchema)
async def get_run(run_id: UUID, db: AsyncSession = Depends(get_db)) -> RunSchema:
    result = await db.execute(
        select(Run).options(selectinload(Run.tasks)).where(Run.id == run_id)
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    run.tasks.sort(key=lambda task: task.index)
    return _to_run_schema(run)


@router.get("/{run_id}/stream")
async def stream_run(run_id: UUID, request: Request) -> StreamingResponse:
    async def event_generator():
        queue: asyncio.Queue[dict] = asyncio.Queue()
        listen_task: asyncio.Task | None = None
        stop_event = asyncio.Event()
        dsn = _asyncpg_dsn()

        async def listen_for_escalations():
            connection = await asyncpg.connect(dsn)  # type: ignore[arg-type]

            def _listener(_conn, _pid, _channel, payload: str):
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    return
                if data.get("run_id") == str(run_id):
                    queue.put_nowait(
                        {
                            "type": "escalation",
                            "task_id": data.get("task_id"),
                            "evidence": data.get("evidence"),
                        }
                    )

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
                    result = await db.execute(
                        select(Run)
                        .options(selectinload(Run.tasks))
                        .where(Run.id == run_id)
                    )
                    run = result.scalar_one_or_none()

                    if run is None:
                        yield "data: " + json.dumps({"type": "error", "message": "Run not found"}) + "\n\n"
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

                    if run.status == "completed" and not run_complete_sent:
                        run_complete_sent = True
                        yield "data: " + json.dumps(
                            {"type": "run_complete", "run_id": str(run.id)}
                        ) + "\n\n"
                        break

                while not queue.empty():
                    event = await queue.get()
                    yield "data: " + json.dumps(event) + "\n\n"

                await asyncio.sleep(1)
        finally:
            stop_event.set()
            if listen_task is not None:
                await asyncio.gather(listen_task, return_exceptions=True)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
