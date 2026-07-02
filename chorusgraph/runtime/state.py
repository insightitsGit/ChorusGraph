"""State merge helpers for the native scheduler."""

from __future__ import annotations

import operator
from typing import Any, Callable, Dict, FrozenSet, Iterable, Optional

DEFAULT_APPEND_KEYS: FrozenSet[str] = frozenset(
    {
        "rule_chain",
        "prism_sequence",
        "hop_metrics",
        "vector_hops",
        "pipeline_trace",
        "tool_calls",
        "conversation_history",
        "agent_trace",
    }
)


def merge_state(
    base: Dict[str, Any],
    update: Dict[str, Any],
    *,
    append_keys: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """Merge a node partial update into accumulated state."""
    keys = frozenset(append_keys or DEFAULT_APPEND_KEYS)
    merged = dict(base)
    for key, value in update.items():
        if key in keys and key in merged:
            left = merged[key]
            if isinstance(left, list) and isinstance(value, list):
                merged[key] = left + value
                continue
        if (
            key not in keys
            and key in merged
            and isinstance(merged[key], list)
            and isinstance(value, list)
        ):
            merged[key] = merged[key] + value
        else:
            merged[key] = value
    return merged


def reducers_from_append_keys(keys: Iterable[str]) -> Dict[str, Callable[[Any, Any], Any]]:
    """Build a reducer map that concatenates lists."""

    def _append(left: Any, right: Any) -> Any:
        if isinstance(left, list) and isinstance(right, list):
            return left + right
        return right if right is not None else left

    return {key: _append for key in keys}


DEFAULT_REDUCERS = reducers_from_append_keys(DEFAULT_APPEND_KEYS)

# LangGraph uses operator.add for Annotated list fields — same behavior.
LIST_ADD_REDUCER = operator.add

__all__ = [
    "DEFAULT_APPEND_KEYS",
    "DEFAULT_REDUCERS",
    "LIST_ADD_REDUCER",
    "merge_state",
    "reducers_from_append_keys",
]
