"""Format Cortex recall for controller injection."""

from __future__ import annotations

from chorusgraph.memory.cortex_service import RecallContext
from chorusgraph.memory.structured_recall import StructuredRecallContext


def format_recall_for_prompt(ctx: RecallContext, *, max_chars: int = 800) -> str:
    """Legacy prose path — prefer format_evidence_for_llm + structured recall."""
    fresh = ctx.freshness.isoformat() if ctx.freshness else "unknown"
    text = (
        f"Recalled memory (confidence={ctx.confidence:.3f}, freshness={fresh}, "
        f"cache_hit={ctx.cache_hit}):\n{ctx.answer}"
    )
    if len(text) > max_chars:
        return text[: max_chars - 3] + "..."
    return text


def format_evidence_for_llm(ctx: StructuredRecallContext, *, max_chars: int = 1200) -> str:
    """Structured facts for the rare LLM boundary — not rendered Cortex prose."""
    from chorusgraph.transforms.templates import format_evidence_block

    text = format_evidence_block(ctx)
    if len(text) > max_chars:
        return text[: max_chars - 3] + "..."
    return text
