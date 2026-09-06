"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    try:
        from app.database import SessionLocal, init_db

        init_db()
        db = SessionLocal()
        try:
            from app.seed import seed_all

            seed_all(db)
            from app.ai.rag import ingest_content_folder

            stats = ingest_content_folder(db)
            log.info("content ingestion: %s", stats)
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001 - the API should still boot
        log.warning("startup initialization skipped: %s", exc)
    log.info(
        "QuantumLearn API ready (gemini=%s, qbraid=%s)",
        bool(settings.gemini_api_key),
        bool(settings.qbraid_api_key and settings.qbraid_device_id),
    )
    yield


app = FastAPI(
    title="QuantumLearn API",
    description="AI-based interactive quantum algorithm learning platform",
    version="0.1.0",
    lifespan=lifespan,
)

_origins = [o.strip() for o in get_settings().api_cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    # credentials cannot be combined with a wildcard origin; JWT travels in a header
    allow_credentials="*" not in _origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {"service": "QuantumLearn API", "docs": "/docs"}
