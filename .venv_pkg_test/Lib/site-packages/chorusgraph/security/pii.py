"""PII redaction for logs and Route Ledger (E3 §21)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Union

_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_PHONE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CREDIT = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

_REDACTED = "[REDACTED]"


def redact_text(text: str) -> str:
    out = _EMAIL.sub(_REDACTED, text)
    out = _PHONE.sub(_REDACTED, out)
    out = _SSN.sub(_REDACTED, out)
    out = _CREDIT.sub(_REDACTED, out)
    return out


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {k: redact_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_value(v) for v in value]
    return value


def redact_ledger_step(step: Dict[str, Any]) -> Dict[str, Any]:
    return redact_value(step)
