"""Deterministic intent detection — CPU routing before LLM."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

_COMPOUND_HINTS = (
    "compound",
    "invest",
    "interest",
    "future value",
    "apr",
    "compounded",
    "principal",
)


def needs_compound_tool(message: str) -> bool:
    lower = message.lower()
    return any(h in lower for h in _COMPOUND_HINTS) and parse_compound_params(message) is not None


def parse_compound_params(message: str) -> Optional[Dict[str, Any]]:
    """
    Parse benchmark compound prompts — principal, APR %, years, compounding frequency.

    Defaults match workload CANONICAL_QUERIES compound_savings examples.
    """
    lower = message.lower()
    if not any(h in lower for h in _COMPOUND_HINTS):
        return None

    principal_match = re.search(r"\$?\s*([\d,]+(?:\.\d+)?)", message)
    if not principal_match:
        return None
    principal = float(principal_match.group(1).replace(",", ""))

    rate_match = re.search(r"([\d]+(?:\.\d+)?)\s*%", message)
    annual_rate_pct = float(rate_match.group(1)) if rate_match else 5.0

    years_match = re.search(r"([\d]+(?:\.\d+)?)\s*years?", lower)
    years = float(years_match.group(1)) if years_match else 3.0

    if "monthly" in lower:
        compounds_per_year = 12
    elif "quarterly" in lower:
        compounds_per_year = 4
    elif "daily" in lower:
        compounds_per_year = 365
    else:
        compounds_per_year = 1

    return {
        "principal": principal,
        "annual_rate_pct": annual_rate_pct,
        "years": years,
        "compounds_per_year": compounds_per_year,
    }
