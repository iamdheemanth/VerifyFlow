from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import socket
from datetime import timedelta
from uuid import uuid4

from app.db.session import AsyncSessionLocal
from app.orchestrator.graph import run_graph
from app.services import run_queue

logger = logging.getLogger(__name__)


def default_worker_id() -> str:
    return f"{socket.gethostname()}-{uuid4()}"


def _heartbeat_interval(lease_seconds: int, explicit_interval: float | None) -> float:
    if explicit_interval is not None:
        return explicit_interval
    return max(1.0, min(30.0, lease_seconds / 3))


async def _renew_lease_until_stopped(
    *,
    run_id: str,
    worker_id: str,
    lease_seconds: int,
    interval_seconds: float,
    stop_event: asyncio.Event,
) -> bool:
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
            break
        except TimeoutError:
            pass

        async with AsyncSessionLocal() as db:
            renewed = await run_queue.renew_claimed_run(
                db,
                run_id=run_id,
                worker_id=worker_id,
                lease_seconds=lease_seconds,
            )
        if not renewed:
            logger.warning("Worker %s lost lease for run %s", worker_id, run_id)
            return False

    return True


async def _run_graph_with_lease_heartbeat(
    *,
    run_id: str,
    worker_id: str,
    lease_seconds: int,
    heartbeat_interval_seconds: float | None = None,
) -> bool:
    stop_event = asyncio.Event()
    graph_task = asyncio.create_task(_run_graph_once(run_id))
    heartbeat_task = asyncio.create_task(
        _renew_lease_until_stopped(
            run_id=run_id,
            worker_id=worker_id,
            lease_seconds=lease_seconds,
            interval_seconds=_heartbeat_interval(lease_seconds, heartbeat_interval_seconds),
            stop_event=stop_event,
        )
    )

    try:
        done, _pending = await asyncio.wait(
            {graph_task, heartbeat_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if heartbeat_task in done and not heartbeat_task.result():
            graph_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await graph_task
            return False

        await graph_task
        return True
    finally:
        stop_event.set()
        if not heartbeat_task.done():
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task


async def _run_graph_once(run_id: str) -> None:
    async with AsyncSessionLocal() as db:
        await run_graph(run_id, db)


async def process_next_run(
    *,
    worker_id: str,
    lease_seconds: int = 1800,
    heartbeat_interval_seconds: float | None = None,
) -> bool:
    async with AsyncSessionLocal() as db:
        run = await run_queue.claim_next_queued_run(
            db,
            worker_id=worker_id,
            lease_seconds=lease_seconds,
        )
        if run is None:
            return False

        run_id = str(run.id)

    try:
        lease_retained = await _run_graph_with_lease_heartbeat(
            run_id=run_id,
            worker_id=worker_id,
            lease_seconds=lease_seconds,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
        )
    except Exception as exc:
        logger.exception("Worker %s failed run %s", worker_id, run_id)
        async with AsyncSessionLocal() as db:
            recorded = await run_queue.record_worker_failure(
                db,
                run_id=run_id,
                worker_id=worker_id,
                exc=exc,
            )
        if not recorded:
            logger.warning("Worker %s skipped failure recording for run %s after losing lease", worker_id, run_id)
        return True

    if not lease_retained:
        logger.warning("Worker %s stopped processing run %s after losing lease", worker_id, run_id)
        return True

    async with AsyncSessionLocal() as db:
        completed = await run_queue.complete_claimed_run(
            db,
            run_id=run_id,
            worker_id=worker_id,
        )
    if not completed:
        logger.warning("Worker %s skipped completion for run %s after losing lease", worker_id, run_id)
    return True


async def recover_stuck_runs(
    *,
    worker_id: str,
    stale_seconds: int,
) -> int:
    async with AsyncSessionLocal() as db:
        recovered = await run_queue.mark_stuck_runs_failed(
            db,
            stale_after=timedelta(seconds=stale_seconds),
            worker_id=worker_id,
        )
    return len(recovered)


async def worker_loop(
    *,
    worker_id: str,
    poll_interval_seconds: float = 2.0,
    lease_seconds: int = 1800,
    heartbeat_interval_seconds: float | None = None,
    stuck_after_seconds: int = 3600,
    once: bool = False,
) -> None:
    logger.info("Starting VerifyFlow run worker %s", worker_id)
    while True:
        recovered_count = await recover_stuck_runs(
            worker_id=worker_id,
            stale_seconds=stuck_after_seconds,
        )
        if recovered_count:
            logger.warning("Worker %s marked %s stuck run(s) failed", worker_id, recovered_count)

        processed = await process_next_run(
            worker_id=worker_id,
            lease_seconds=lease_seconds,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
        )

        if once:
            return

        if not processed:
            await asyncio.sleep(poll_interval_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run queued VerifyFlow jobs.")
    parser.add_argument("--worker-id", default=default_worker_id())
    parser.add_argument("--poll-interval-seconds", type=float, default=2.0)
    parser.add_argument("--lease-seconds", type=int, default=1800)
    parser.add_argument("--heartbeat-interval-seconds", type=float, default=None)
    parser.add_argument("--stuck-after-seconds", type=int, default=3600)
    parser.add_argument("--once", action="store_true", help="Process at most one queued run and exit.")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    try:
        asyncio.run(
            worker_loop(
                worker_id=args.worker_id,
                poll_interval_seconds=args.poll_interval_seconds,
                lease_seconds=args.lease_seconds,
                heartbeat_interval_seconds=args.heartbeat_interval_seconds,
                stuck_after_seconds=args.stuck_after_seconds,
                once=args.once,
            )
        )
    except KeyboardInterrupt:
        logger.info("VerifyFlow run worker stopped")


if __name__ == "__main__":
    main()
