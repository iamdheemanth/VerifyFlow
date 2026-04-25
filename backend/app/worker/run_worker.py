from __future__ import annotations

import argparse
import asyncio
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


async def process_next_run(
    *,
    worker_id: str,
    lease_seconds: int = 1800,
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
        async with AsyncSessionLocal() as db:
            await run_graph(run_id, db)
    except Exception as exc:
        logger.exception("Worker %s failed run %s", worker_id, run_id)
        async with AsyncSessionLocal() as db:
            await run_queue.record_worker_failure(
                db,
                run_id=run_id,
                worker_id=worker_id,
                exc=exc,
            )
        return True

    async with AsyncSessionLocal() as db:
        await run_queue.complete_claimed_run(db, run_id=run_id)
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
                stuck_after_seconds=args.stuck_after_seconds,
                once=args.once,
            )
        )
    except KeyboardInterrupt:
        logger.info("VerifyFlow run worker stopped")


if __name__ == "__main__":
    main()
