# app/middlewares/logging.py
import logging
import time
import re
from typing import Any, Dict, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Update

logger = logging.getLogger("app.middleware.logging")

INVOICE_RE = re.compile(r"(?:^|[\s:/])([0-9a-f]{32})\b", re.IGNORECASE)

def _safe_get(obj: Any, path: str, default: Any = None):
    cur = obj
    for p in path.split("."):
        if cur is None:
            return default
        cur = getattr(cur, p, None)
    return cur if cur is not None else default

def _extract_invoice_from_event(event: Any) -> str | None:
    # из текста сообщения
    text = getattr(event, "text", None) or getattr(getattr(event, "message", None), "text", None)
    if isinstance(text, str):
        m = INVOICE_RE.search(text)
        if m:
            return m.group(1)

    # из callback.data
    data = getattr(event, "data", None)
    if isinstance(data, str):
        m = INVOICE_RE.search(data)
        if m:
            return m.group(1)
    return None

class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        # Достаём Update, если он есть в данных
        update: Update | None = data.get("event_update") or data.get("update")
        update_id = getattr(update, "update_id", "-")

        user_id = (
            _safe_get(event, "from_user.id")
            or _safe_get(event, "message.from_user.id")
            or "-"
        )
        chat_id = (
            _safe_get(event, "chat.id")
            or _safe_get(event, "message.chat.id")
            or "-"
        )
        msg_id = (
            _safe_get(event, "message_id")
            or _safe_get(event, "message.message_id")
            or _safe_get(event, "id")  # на крайняк
            or "-"
        )
        invoice_id = _extract_invoice_from_event(event) or "-"

        # входящий лог
        logger.info(
            "incoming",
            extra={
                "update_id": update_id,
                "user_id": user_id,
                "chat_id": chat_id,
                "message_id": msg_id,
                "invoice_id": invoice_id,
                "event_type": type(event).__name__,
            },
        )

        started = time.perf_counter()
        try:
            result = await handler(event, data)
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "handled",
                extra={
                    "update_id": update_id,
                    "user_id": user_id,
                    "chat_id": chat_id,
                    "message_id": msg_id,
                    "invoice_id": invoice_id,
                    "event_type": type(event).__name__,
                    "duration_ms": duration_ms,
                },
            )
            return result
        except Exception:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.exception(
                "handler_error",
                extra={
                    "update_id": update_id,
                    "user_id": user_id,
                    "chat_id": chat_id,
                    "message_id": msg_id,
                    "invoice_id": invoice_id,
                    "event_type": type(event).__name__,
                    "duration_ms": duration_ms,
                },
            )
            raise
