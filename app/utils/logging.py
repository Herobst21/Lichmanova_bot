# app/utils/logging.py
from __future__ import annotations
import logging
import os
import sys
from datetime import datetime

def setup_json_logging():
    level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    json_mode = str(os.getenv("LOG_JSON", "false")).lower() in {"1","true","yes"}
    root = logging.getLogger()
    root.setLevel(level)

    # зачистим хендлеры (uvicorn любит навешивать свои)
    for h in list(root.handlers):
        root.removeHandler(h)

    if json_mode:
        try:
            from pythonjsonlogger import jsonlogger
        except Exception:
            json_mode = False

    handler = logging.StreamHandler(sys.stdout)

    if json_mode:
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            json_ensure_ascii=False
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    handler.setFormatter(formatter)
    root.addHandler(handler)

    logging.getLogger("uvicorn").setLevel(level)
    logging.getLogger("uvicorn.error").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(level)
    logging.getLogger("asyncio").setLevel(level)

    logging.getLogger(__name__).info("logging_ready", extra={
        "json": json_mode, "level": logging.getLevelName(level),
        "ts": datetime.utcnow().isoformat()+"Z"
    })
