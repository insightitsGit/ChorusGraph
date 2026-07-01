"""Format Cortex recall for controller injection."""

from __future__ import annotations

from chorusgraph.memory.cortex_service import RecallContext


def format_recall_for_prompt(ctx: RecallContext, *, max_chars: int = 800) -> str:
    fresh = ctx.freshness.isoformat() if ctx.freshness else "unknown"
    text = (
        f"Recalled memory (confidence={ctx.confidence:.3f}, freshness={fresh}, "
        f"cache_hit={ctx.cache_hit}):\n{ctx.answer}"
    )
    if len(text) > max_chars:
        return text[: max_chars - 3] + "..."
    return text
