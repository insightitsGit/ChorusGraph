# HC1 vs HL1 / FC1 — parity and latency

## Why FC1 is ~4× faster than FL1 but HC1 ≈ HL1

| Factor | Finance (FL1 → FC1) | Healthcare single (HL1 → HC1) |
|--------|---------------------|-------------------------------|
| **Semantic cache** | FC1: **~48% hit rate** | HC1 (before fix): **0%** |
| **Avg LLM calls/task** | 3.3 → **0.9** | 3.0 → **3.0** |
| **Mean latency** | 5194 → **1386 ms** | 6798 → **6742 ms** (~1%) |

**Conclusion:** FC1’s win is mostly **cache skipping Gemini**, not the core scheduler. HC1 had no `cache_gate` and identical LLM work — engine overhead is noise vs API latency.

Canonical run `20260703_042206` (pre-HC1-cache): HL1 and HC1 tied at **72.5%** success with matched LLM/tool calls.

## Engine bugs fixed (2026-07-03)

1. **Resonance routing** — ambiguous `general` slug forced `react → react` loop (6 LLM calls, 0% success). Fixed: Resonance only when exactly one subscriber matches.
2. **Channel state** — `pending_action` (dict) was dropped from `view()`; router never saw tool requests. Fixed: dict/list artifacts persist in `_scalars`.
3. **Type normalization** — use `int()` / `bool()` on `react_step`, `tool_calls`, `react_done` when reading state.

## HC1 cache (parity with FC1)

HC1 includes:

- `cache_gate` node (clinical slug, depth-aware keys)
- Per-session `FinanceRuntime` cache (same gate thresholds as FC2)
- Session cache seeding after successful runs (repeat / paraphrase band)

Re-run the 40-task benchmark to measure cache hit rate and latency vs HL1. On the 40% repeat band, expect FC1-style gains on warm sessions (~70% of tasks in a session after the first).

## Fair comparison checklist

| Capability | FL1 | FC1 | HL1 | HC1 |
|------------|-----|-----|-----|-----|
| ReAct loop | ✓ | ✓ | ✓ | ✓ |
| Same prompts | ✓ | ✓ | ✓ | ✓ |
| Semantic cache | ✗ | ✓ | ✗ | ✓ |
| Native engine | ✗ | **core.Graph** | ✗ | **core.Graph** |

FC1 graph: `chorusgraph/examples/finance_agent/patterns_graph.py` (native, no LangGraph). See [`docs/TERMINOLOGY.md`](../../docs/TERMINOLOGY.md).
