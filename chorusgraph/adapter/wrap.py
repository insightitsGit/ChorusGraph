"""Adapter — native CompiledGraph ledger + legacy LangGraph fallback."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from chorusgraph.ledger.models import LedgerStep, RouteLedger
from chorusgraph.ledger.sink import LedgerSink, SqliteLedgerSink

_APPEND_KEYS = frozenset(
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


def _merge_state(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in update.items():
        if key in _APPEND_KEYS and key in merged:
            left = merged[key]
            if isinstance(left, list) and isinstance(value, list):
                merged[key] = left + value
                continue
        if (
            key not in _APPEND_KEYS
            and key in merged
            and isinstance(merged[key], list)
            and isinstance(value, list)
        ):
            merged[key] = merged[key] + value
        else:
            merged[key] = value
    return merged


def _parse_edge_from_triggers(triggers: Optional[List[str]]) -> Optional[str]:
    if not triggers:
        return None
    for trigger in triggers:
        if trigger.startswith("branch:to:"):
            return trigger.split(":", 2)[-1]
    return None


def _extract_grounding_score(
    result: Dict[str, Any],
    node_name: str,
    *,
    merged_state: Optional[Dict[str, Any]] = None,
) -> Optional[float]:
    if node_name != "writer":
        return None
    if result.get("memory_confidence") is not None:
        return float(result["memory_confidence"])
    if merged_state is not None and merged_state.get("memory_confidence") is not None:
        return float(merged_state["memory_confidence"])
    return None


def _append_agent_trace_steps(
    ledger: RouteLedger,
    node: str,
    result: Dict[str, Any],
    *,
    timestamp: datetime,
) -> None:
    trace = result.get("agent_trace") or []
    for step in trace:
        if isinstance(step, dict):
            kind = step.get("kind") or "step"
            content = step.get("content") or ""
        else:
            kind = getattr(step, "kind", "step")
            if hasattr(kind, "value"):
                kind = kind.value
            content = getattr(step, "content", str(step))
        ledger.add_step(
            LedgerStep(
                node=f"{node}/{kind}",
                rule_chain=[content[:500] if content else kind],
                timestamp=timestamp,
            )
        )


def _extract_rule_chain(
    result: Dict[str, Any],
    node_name: str,
    *,
    merged_state: Optional[Dict[str, Any]] = None,
) -> Optional[List[str]]:
    chain = result.get("rule_chain")
    if chain:
        return list(chain)

    sequence = result.get("prism_sequence") or []
    if not sequence and merged_state is not None:
        sequence = merged_state.get("prism_sequence") or []
    for envelope in reversed(sequence):
        if envelope.get("agent_id") == node_name and envelope.get("rule_chain"):
            return list(envelope["rule_chain"])
    return None


class RunnableWithLedger:
    """Wraps a compiled graph and ensures Route Ledger persistence."""

    def __init__(
        self,
        compiled_graph: Any,
        *,
        tenant_id: str,
        graph_id: str,
        sink: Optional[LedgerSink] = None,
    ) -> None:
        self._graph = compiled_graph
        self._tenant_id = tenant_id
        self._graph_id = graph_id
        self._sink = sink or SqliteLedgerSink()
        self.last_ledger: Optional[RouteLedger] = None

        if getattr(compiled_graph, "_native", False):
            compiled_graph.attach_ledger(
                tenant_id=tenant_id,
                graph_id=graph_id,
                sink=self._sink,
            )

    @property
    def graph(self) -> Any:
        return self._graph

    def invoke(self, input: Dict[str, Any], /, **kwargs: Any) -> Dict[str, Any]:
        if getattr(self._graph, "_native", False):
            result = self._graph.invoke(input, **kwargs)
            self.last_ledger = self._graph.last_ledger
            return result
        return self._run_legacy(input, kwargs, async_mode=False)

    async def ainvoke(self, input: Dict[str, Any], /, **kwargs: Any) -> Dict[str, Any]:
        if getattr(self._graph, "_native", False):
            result = await self._graph.ainvoke(input, **kwargs)
            self.last_ledger = self._graph.last_ledger
            return result
        return await self._run_legacy_async(input, kwargs)

    def _run_legacy(self, input: Dict[str, Any], kwargs: Dict[str, Any], *, async_mode: bool) -> Dict[str, Any]:
        run_id = str(uuid4())
        turn_id = input.get("turn_id") or input.get("request_id")
        ledger = RouteLedger(
            run_id=run_id,
            turn_id=str(turn_id) if turn_id else None,
            tenant_id=self._tenant_id,
            graph_id=self._graph_id,
        )

        state = dict(input)
        final_state: Dict[str, Any] = state
        pending: Dict[str, float] = {}

        stream_kwargs = dict(kwargs)
        stream_kwargs["stream_mode"] = "debug"

        for event in self._graph.stream(state, **stream_kwargs):
            if not isinstance(event, dict):
                continue
            event_type = event.get("type")
            payload = event.get("payload") or {}

            if event_type == "task":
                node = payload.get("name")
                if not node:
                    continue
                pending[node] = time.perf_counter()
                edge_taken = _parse_edge_from_triggers(payload.get("triggers"))
                if edge_taken and ledger.steps:
                    ledger.steps[-1].edge_taken = edge_taken

            elif event_type == "task_result":
                node = payload.get("name")
                if not node:
                    continue
                started = pending.pop(node, time.perf_counter())
                duration_ms = int((time.perf_counter() - started) * 1000)
                result = payload.get("result") or {}
                if isinstance(result, dict):
                    state = _merge_state(state, result)
                    final_state = state
                ts_raw = event.get("timestamp")
                timestamp = (
                    datetime.fromisoformat(ts_raw)
                    if isinstance(ts_raw, str)
                    else datetime.now(timezone.utc)
                )
                ledger.add_step(
                    LedgerStep(
                        node=node,
                        edge_taken=None,
                        rule_chain=_extract_rule_chain(result, node, merged_state=state),
                        duration_ms=duration_ms,
                        timestamp=timestamp,
                        grounding_score=_extract_grounding_score(result, node, merged_state=state),
                    )
                )
                if isinstance(result, dict) and result.get("agent_trace"):
                    _append_agent_trace_steps(ledger, node, result, timestamp=timestamp)

        self._sink.write(ledger)
        self.last_ledger = ledger
        return final_state

    async def _run_legacy_async(self, input: Dict[str, Any], kwargs: Dict[str, Any]) -> Dict[str, Any]:
        return self._run_legacy(input, kwargs, async_mode=True)


def wrap(
    compiled_graph: Any,
    *,
    tenant_id: str,
    graph_id: str,
    sink: Optional[LedgerSink] = None,
) -> RunnableWithLedger:
    """Attach Route Ledger tracking to a compiled graph."""
    return RunnableWithLedger(
        compiled_graph,
        tenant_id=tenant_id,
        graph_id=graph_id,
        sink=sink,
    )


__all__ = ["RunnableWithLedger", "wrap"]
