"""Career Assistant — FastAPI entrypoint."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.errors import register_exception_handlers
from app.core.llm import configure_langsmith
from app.logging_config import configure_logging, get_logger, new_request_id, set_request_id
from app.routers import health, sessions

configure_logging()
log = get_logger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info(
        "Starting %s v%s (env=%s)", settings.app_name, settings.app_version, settings.environment
    )
    configure_langsmith()
    from app.graph.build import active_checkpointer_name

    log.info(
        "AI enabled=%s provider=%s | checkpointer=%s",
        settings.ai_enabled,
        settings.llm_provider,
        active_checkpointer_name(),
    )
    yield
    log.info("Shutting down.")


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    rid = request.headers.get("x-request-id") or new_request_id()
    set_request_id(rid)
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["x-request-id"] = rid
    log.info(
        "%s %s -> %s (%.0f ms)",
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - started) * 1000,
    )
    return response


register_exception_handlers(app)
app.include_router(health.router)
app.include_router(sessions.router)


@app.get("/", tags=["health"])
def root():
    return {"service": settings.app_name, "version": settings.app_version, "docs": "/docs"}
