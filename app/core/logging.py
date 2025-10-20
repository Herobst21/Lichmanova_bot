import logging
import sys
import os
from logging.config import dictConfig


def setup_logging() -> None:
    """Базовая настройка логирования всего приложения."""
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    json_fmt = os.getenv("LOG_JSON", "0") == "1"

    if json_fmt:
        fmt = (
            '{"ts":"%(asctime)s","lvl":"%(levelname)s","name":"%(name)s",'
            '"msg":"%(message)s","update_id":"%(update_id)s",'
            '"user_id":"%(user_id)s","invoice_id":"%(invoice_id)s"}'
        )
    else:
        fmt = (
            "%(asctime)s | %(levelname)5s | %(name)s | %(message)s "
            "| upd=%(update_id)s user=%(user_id)s inv=%(invoice_id)s"
        )

    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"default": {"format": fmt}},
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "default",
            }
        },
        "root": {"level": level, "handlers": ["stdout"]},
        "loggers": {
            # Для SQLAlchemy можно включить подробности при отладке:
            "sqlalchemy.engine": {
                "level": os.getenv("LOG_SQL", "WARNING").upper()
            },
            # Для aiogram — INFO или DEBUG, если нужно видеть апдейты:
            "aiogram": {
                "level": os.getenv("LOG_AIOGRAM", "INFO").upper()
            },
            # Для наших модулей:
            "app": {"level": level},
        },
    })


class CtxFilter(logging.Filter):
    """Добавляет безопасные поля, чтобы форматтер не падал, когда нет extra."""
    def filter(self, record: logging.LogRecord) -> bool:
        for k in ("update_id", "user_id", "invoice_id"):
            if not hasattr(record, k):
                setattr(record, k, "-")
        return True


def attach_ctx_filter() -> None:
    """Подключает фильтр к каждому хендлеру, чтобы extra всегда был безопасен."""
    f = CtxFilter()
    for h in logging.getLogger().handlers:
        h.addFilter(f)
