# app/web/server.py
from __future__ import annotations

import os
import socket
import platform
import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import uvicorn

from app.config import settings
from app.utils.logging import setup_json_logging
from app.web.middleware_logging import LoggingMiddleware
from app.web.errors import unhandled_exception_handler
from app.web.routes import router as api_router
from app.web.robokassa_routes import (
    router as rk_router,
    debug_router as rk_debug_router,
)

log = logging.getLogger("startup")

app = FastAPI(title="CS2 Farm WebApp")

# Middleware
app.add_middleware(LoggingMiddleware)

# Routers
app.include_router(api_router)   # базовые API-роуты
app.include_router(rk_router)    # боевые роуты Robokassa
if os.getenv("DEBUG_ROUTES", "0") == "1":
    app.include_router(rk_debug_router)  # диагностические ручки Robokassa


def _safe(attr: str, default=""):
    return getattr(settings, attr, default) or default


@app.on_event("startup")
async def on_startup():
    setup_json_logging()

    host = socket.gethostname()
    try:
        ip = socket.gethostbyname(host)
    except Exception:
        ip = "unknown"

    env_snapshot = {
        "WEBAPP_HOST": os.getenv("WEBAPP_HOST"),
        "WEBAPP_PORT": os.getenv("WEBAPP_PORT"),
        "PUBLIC_BASE_URL": _safe("PUBLIC_BASE_URL", ""),
        "ROBOKASSA_LOGIN_tail": (_safe("ROBOKASSA_LOGIN")[-4:] if _safe("ROBOKASSA_LOGIN") else ""),
        "P1_len": len(_safe("ROBOKASSA_PASSWORD1", "")),
        "P2_len": len(_safe("ROBOKASSA_PASSWORD2", "")),
        "RK_TEST": _safe("ROBOKASSA_TEST", 1),
        "DEBUG_ROUTES": os.getenv("DEBUG_ROUTES", "0"),
    }

    log.info(
        "app_startup | platform=%s python=%s hostname=%s ip=%s env=%s",
        platform.platform(),
        platform.python_version(),
        host,
        ip,
        env_snapshot,
    )


@app.exception_handler(Exception)
async def _unhandled(request, exc):
    return await unhandled_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def _validation(request, exc: RequestValidationError):
    rid = getattr(request.state, "request_id", "-")
    logging.getLogger("errors").warning(
        "validation_error rid=%s detail=%s", rid, exc.errors()
    )
    return JSONResponse(
        {"ok": False, "error": "validation_error", "detail": exc.errors(), "rid": rid},
        status_code=422,
    )


if __name__ == "__main__":
    uvicorn.run(
        "app.web.server:app",
        host=_safe("WEBAPP_HOST", "0.0.0.0"),
        port=int(_safe("WEBAPP_PORT", 8080)),
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        access_log=True,
    )
