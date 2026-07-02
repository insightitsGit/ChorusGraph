"""Native Pregel-style scheduler — ChorusGraph execution engine."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Dict, Iterator, Optional

from chorusgraph.engine.context import PrismEngineContext
from chorusgraph.graph.ir import GraphIR
from chorusgraph.runtime.constants import END
from chorusgraph.runtime.state import DEFAULT_APPEND_KEYS, merge_state
from chorusgraph.transport.spine import TransportSpine, build_spine


class CompiledGraph:
    """
    Compiled native graph runnable (DESIGN §5.2).

    Exposes ``invoke`` / ``stream`` compatible with the Route Ledger adapter.
    """

    def __init__(
        self,
        ir: GraphIR,
        *,
        checkpointer: Any = None,
        reducers: Optional[Dict[str, Callable[[Any, Any], Any]]] = None,
        context: Optional[PrismEngineContext] = None,
    ) -> None:
        self._ir = ir
        self._checkpointer = checkpointer
        self._reducers = reducers or {}
        self._context = context
        self._spine = build_spine(context)
        self._native = True

    @property
    def ir(self) -> GraphIR:
        return self._ir

    def invoke(self, input: Dict[str, Any], /, **kwargs: Any) -> Dict[str, Any]:
        state = dict(input)
        current = self._ir.entry
        while current and current != END:
            if current not in self._ir.nodes:
                raise KeyError(f"Graph references unknown node: {current}")
            result = self._ir.nodes[current](state)
            if not isinstance(result, dict):
                raise TypeError(f"Node {current!r} must return dict, got {type(result).__name__}")
            state = merge_state(state, result, append_keys=DEFAULT_APPEND_KEYS)
            next_node = self._ir.successor(current, state)
            if next_node and next_node != END:
                transport_update = self._apply_edge_transport(current, next_node, state)
                if transport_update:
                    state = merge_state(state, transport_update, append_keys=DEFAULT_APPEND_KEYS)
            current = next_node
        return state

    async def ainvoke(self, input: Dict[str, Any], /, **kwargs: Any) -> Dict[str, Any]:
        state = dict(input)
        for update in self._run_nodes(state):
            state = merge_state(state, update, append_keys=DEFAULT_APPEND_KEYS)
            await asyncio.sleep(0)
        return state

    def stream(self, input: Dict[str, Any], /, **kwargs: Any) -> Iterator[Dict[str, Any]]:
        stream_mode = kwargs.get("stream_mode", "values")
        if stream_mode != "debug":
            yield from self._stream_values(input)
            return
        yield from self._stream_debug(input)

    async def astream(
        self, input: Dict[str, Any], /, **kwargs: Any
    ) -> AsyncIterator[Dict[str, Any]]:
        stream_mode = kwargs.get("stream_mode", "values")
        if stream_mode != "debug":
            for event in self._stream_values(input):
                yield event
            return
        for event in self._stream_debug(input):
            yield event
            await asyncio.sleep(0)

    def _stream_values(self, input: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        state = dict(input)
        for update in self._run_nodes(state):
            state = merge_state(state, update, append_keys=DEFAULT_APPEND_KEYS)
            yield dict(state)

    def _stream_debug(self, input: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        state = dict(input)
        current = self._ir.entry
        if not current:
            return

        while current and current != END:
            if current not in self._ir.nodes:
                raise KeyError(f"Graph references unknown node: {current}")

            yield {
                "type": "task",
                "payload": {
                    "name": current,
                    "triggers": [f"branch:to:{current}"],
                },
            }

            handler = self._ir.nodes[current]
            result = handler(state)
            if not isinstance(result, dict):
                raise TypeError(f"Node {current!r} must return dict, got {type(result).__name__}")
            state = merge_state(state, result, append_keys=DEFAULT_APPEND_KEYS)

            ts = datetime.now(timezone.utc).isoformat()
            yield {
                "type": "task_result",
                "timestamp": ts,
                "payload": {"name": current, "result": result},
            }

            from_node = current
            next_node = self._ir.successor(from_node, state)
            if next_node and next_node != END:
                transport_update = self._apply_edge_transport(from_node, next_node, state)
                if transport_update:
                    state = merge_state(state, transport_update, append_keys=DEFAULT_APPEND_KEYS)
            current = next_node

    def _apply_edge_transport(
        self, from_node: str, to_node: Optional[str], state: Dict[str, Any]
    ) -> Dict[str, Any]:
        if self._spine is None or not to_node or to_node == END:
            return {}
        mode = self._ir.transport_for(from_node)
        return self._spine.edge_handoff(
            mode=mode,
            from_hop=from_node,
            to_hop=to_node,
            state=state,
        )

    def _run_nodes(self, state: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        current = self._ir.entry
        while current and current != END:
            if current not in self._ir.nodes:
                raise KeyError(f"Graph references unknown node: {current}")
            result = self._ir.nodes[current](state)
            if not isinstance(result, dict):
                raise TypeError(f"Node {current!r} must return dict, got {type(result).__name__}")
            yield result
            state = merge_state(state, result, append_keys=DEFAULT_APPEND_KEYS)
            next_node = self._ir.successor(current, state)
            if next_node and next_node != END:
                transport_update = self._apply_edge_transport(current, next_node, state)
                if transport_update:
                    state = merge_state(state, transport_update, append_keys=DEFAULT_APPEND_KEYS)
            current = next_node


__all__ = ["CompiledGraph"]
