# app/web/errors.py
from __future__ import annotations
import logging, traceback
from fastapi import Request
from fastapi.responses import JSONResponse

log = logging.getLogger("errors")

async def unhandled_exception_handler(request: Request, exc: Exception):
    rid = getattr(request.state, "request_id", "-")
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    log.error("unhandled_exception", extra={"rid": rid, "path": request.url.path, "error": str(exc)})
    # не палим детали наружу, но даем признак
    return JSONResponse({"ok": False, "error": "internal_error", "rid": rid}, status_code=500)
