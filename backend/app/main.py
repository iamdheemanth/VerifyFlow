from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.benchmarks import router as benchmarks_router
from app.routes.configurations import router as configurations_router
from app.routes.demo import router as demo_router
from app.routes.ledger import router as ledger_router
from app.routes.review import router as review_router
from app.routes.runs import router as runs_router


def configure_logging() -> None:
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s: %(message)s",
        )
    root_logger.setLevel(logging.INFO)


configure_logging()

app = FastAPI(title="VerifyFlow API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs_router, prefix="/api")
app.include_router(ledger_router, prefix="/api")
app.include_router(review_router, prefix="/api")
app.include_router(benchmarks_router, prefix="/api")
app.include_router(configurations_router, prefix="/api")
app.include_router(demo_router, prefix="/api")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
