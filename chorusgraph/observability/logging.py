"""Structured JSON logging with correlation IDs (E4)."""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
_run_id: ContextVar[Optional[str]] = ContextVar("run_id", default=None)


def set_correlation(*, correlation_id: str, run_id: Optional[str] = None) -> None:
    _correlation_id.set(correlation_id)
    if run_id is not None:
        _run_id.set(run_id)


def get_correlation_id() -> Optional[str]:
    return _correlation_id.get()


def get_run_id() -> Optional[str]:
    return _run_id.get()


class JsonLogFormatter(logging.Formatter):
    """Emit one JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        cid = get_correlation_id()
        rid = get_run_id()
        if cid:
            payload["correlation_id"] = cid
        if rid:
            payload["run_id"] = rid
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_structured_logging(*, level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    root = logging.getLogger("chorusgraph")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False
