"""FastAPI application entry point.

Run locally: `uv run uvicorn app.main:app --reload` from `Robot/api/`.
"""

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.config import settings
from app.routers import health, loads
from app.services.load_store import load_store


def configure_logging() -> None:
    """structlog → JSON to stdout. Replaces stdlib logging handler."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    load_store.load(settings.loads_json_path)
    log.info("startup", loads_loaded=len(load_store.all()))
    yield
    log.info("shutdown")


app = FastAPI(
    title="Robot API",
    version="0.0.1",
    description="Inbound carrier voice-agent backend (HappyRobot integration).",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(loads.router, prefix="/v1")
