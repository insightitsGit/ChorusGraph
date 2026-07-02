"""Canonical-id rubric — scores answer against intended task, not any decimal."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from chorusgraph.transforms.intent import parse_compound_params

_FV_TOLERANCE = 1.0  # dollars
_CANONICAL_FV = 11614.72  # workload default: 10k @ 5% monthly 3y


def _has_decimal(text: str) -> bool:
    return bool(re.search(r"\d+\.\d+", text))


def _amount_near(text: str, target: float, *, tol: float = _FV_TOLERANCE) -> bool:
    for match in re.findall(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+\.\d+", text):
        val = float(match.replace(",", ""))
        if abs(val - target) <= tol:
            return True
    return False


def _score_fx_pair(answer: str, from_c: str, to_c: str, tool_result: Optional[Dict[str, Any]]) -> bool:
    upper = answer.upper()
    if from_c not in upper or to_c not in upper:
        return False
    if not _has_decimal(answer):
        return False
    if tool_result and tool_result.get("rate") is not None:
        rate = float(tool_result["rate"])
        if not _amount_near(answer, rate, tol=0.01):
            return False
    return True


def score_by_canonical(
    *,
    canonical_id: str,
    message: str,
    answer: str,
    tool_result: Optional[Dict[str, Any]] = None,
) -> bool:
    text = (answer or "").strip()
    if len(text) < 10:
        return False

    if canonical_id == "compound_savings":
        params = parse_compound_params(message)
        if params and tool_result and tool_result.get("future_value") is not None:
            expected = float(tool_result["future_value"])
        elif params:
            from chorusgraph.nodes.tool import compound_interest

            expected = float(compound_interest(**params)["future_value"])
        else:
            expected = _CANONICAL_FV
        return _amount_near(text, expected)

    if canonical_id == "usd_eur":
        return _score_fx_pair(text, "USD", "EUR", tool_result)
    if canonical_id == "usd_gbp":
        return _score_fx_pair(text, "USD", "GBP", tool_result)
    if canonical_id == "eur_gbp":
        return _score_fx_pair(text, "EUR", "GBP", tool_result)
    if canonical_id == "usd_jpy":
        return _score_fx_pair(text, "USD", "JPY", tool_result)
    if canonical_id == "compare_usd_eur_gbp":
        if not (_has_decimal(text) and "EUR" in text.upper() and "GBP" in text.upper()):
            return False
        if tool_result:
            return True
        return text.upper().count("USD") >= 1

    return _has_decimal(text)
