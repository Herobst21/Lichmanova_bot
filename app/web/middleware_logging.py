# app/web/middleware_logging.py
from __future__ import annotations
import logging, time, uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

log = logging.getLogger("http")

SAFE_HEADERS = {"content-type", "user-agent", "x-request-id", "x-real-ip", "x-forwarded-for"}

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        start = time.perf_counter()
        scope = request.scope
        method = scope.get("method")
        path = scope.get("path")
        client = scope.get("client")
        addr = f"{client[0]}:{client[1]}" if client else "?:?"

        # Часть заголовков
        headers = {k.lower(): v for k, v in request.headers.items() if k.lower() in SAFE_HEADERS}
        ctype = headers.get("content-type","")

        # Пытаемся понять размер body без чтения
        try:
            clen = int(request.headers.get("content-length","0"))
        except Exception:
            clen = 0

        log.info("http_request", extra={
            "rid": rid, "method": method, "path": path,
            "client": addr, "ctype": ctype, "clen": clen
        })

        # Прокидываем request-id дальше
        request.state.request_id = rid

        try:
            response: Response = await call_next(request)
            elapsed = (time.perf_counter() - start) * 1000
            log.info("http_response", extra={
                "rid": rid, "status": response.status_code, "ms": round(elapsed,2),
                "path": path
            })
            response.headers["x-request-id"] = rid
            return response
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            log.exception("http_error", extra={
                "rid": rid, "path": path, "ms": round(elapsed,2)
            })
            raise
