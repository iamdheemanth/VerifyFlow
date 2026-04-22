from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.auth import verify_token
from app.routes._contracts import build_api_error, error_code_for_status
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

app = FastAPI(
    title="VerifyFlow API",
    dependencies=[Depends(verify_token)],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d+)?$",
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


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        payload = exc.detail
    else:
        message = str(exc.detail)
        payload = build_api_error(error_code_for_status(exc.status_code), message)
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger(__name__).exception("Unhandled API error", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=build_api_error("internal_error", "An unexpected backend error occurred."),
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
