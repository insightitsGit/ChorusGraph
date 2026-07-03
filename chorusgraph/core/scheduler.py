"""Bulk-synchronous scheduler — the Prism engine (ENGINE §3.1, P1–P4)."""

from __future__ import annotations

import asyncio
import inspect
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Set, Tuple, Union
from uuid import uuid4

from prismlang import PrismProjector

from chorusgraph.core.bus import ResonanceBus
from chorusgraph.core.cache_interceptor import CacheInterceptor
from chorusgraph.core.channels import ChannelState, NodeUpdate
from chorusgraph.core.ir import GraphIR
from chorusgraph.core.node import NodeContext, NodeInterrupt
from chorusgraph.core.persistence import EngineCheckpointer, GraphStateSnapshot, state_from_checkpoint
from chorusgraph.core.trace import RouteTracker
from chorusgraph.core.transport_router import TransportRouter
from chorusgraph.ledger.sink import LedgerSink


class GraphInterrupt(Exception):
    """Raised when execution halts at a HITL boundary."""

    def __init__(
        self,
        state: Dict[str, Any],
        *,
        next_nodes: Set[str],
        super_step: int,
        payload: Any = None,
    ) -> None:
        self.state = state
        self.next_nodes = next_nodes
        self.super_step = super_step
        self.payload = payload
        super().__init__(f"Graph interrupted before {sorted(next_nodes)}")


@dataclass
class EngineConfig:
    recursion_limit: int = 25
    graph_id: str = "graph"
    tenant_id: str = "default"


@dataclass
class RunResult:
    values: Dict[str, Any]
    events: List[Dict[str, Any]]
    interrupted: bool = False
    next_nodes: Set[str] = field(default_factory=set)


@dataclass
class CompiledGraph:
    """Compiled native graph — envelope channels + Resonance bus."""

    ir: GraphIR
    bus: ResonanceBus
    projector: Optional[PrismProjector] = None
    config: EngineConfig = field(default_factory=EngineConfig)
    checkpointer: Optional[EngineCheckpointer] = None
    ledger_sink: Optional[LedgerSink] = None
    cache_interceptor: Optional[CacheInterceptor] = None
    transport: Optional[TransportRouter] = None
    _native: bool = True

    last_ledger: Optional[Any] = None
    last_tracker: Optional[RouteTracker] = None
    _tracker: Optional[RouteTracker] = field(default=None, repr=False)
    _llm_calls: int = field(default=0, repr=False)
    _last_run_result: Optional[RunResult] = field(default=None, repr=False)
    _step_next_active: Set[str] = field(default_factory=set, repr=False)

    def attach_ledger(
        self,
        *,
        tenant_id: Optional[str] = None,
        graph_id: Optional[str] = None,
        sink: Optional[LedgerSink] = None,
    ) -> "CompiledGraph":
        if tenant_id:
            self.config.tenant_id = tenant_id
        if graph_id:
            self.config.graph_id = graph_id
        if sink is not None:
            self.ledger_sink = sink
        return self

    @property
    def llm_calls(self) -> int:
        return self._llm_calls

    def get_state(self, config: Dict[str, Any]) -> GraphStateSnapshot:
        if self.checkpointer is None:
            raise RuntimeError("No checkpointer configured")
        tup = self.checkpointer.get_tuple(config)
        if tup is None:
            return GraphStateSnapshot(values={}, next=(), config=dict(config))
        meta = tup.metadata or {}
        active = tuple(meta.get("active_nodes") or ())
        return GraphStateSnapshot(
            values=dict(tup.checkpoint.get("channel_values") or {}),
            next=active,
            config=dict(tup.config or config),
            metadata=dict(meta),
            created_at=tup.checkpoint.get("ts"),
            parent_config=tup.parent_config,
        )

    def update_state(
        self,
        config: Dict[str, Any],
        values: Dict[str, Any],
        *,
        as_node: Optional[str] = None,
    ) -> GraphStateSnapshot:
        current = self.get_state(config)
        merged = {**current.values, **values}
        state = ChannelState.from_checkpoint_values(merged)
        active = set(current.next) if current.next else ({as_node} if as_node else set())
        new_config = dict(config)
        if self.checkpointer is not None:
            new_config = self.checkpointer.fork(
                config,
                state,
                super_step=int(current.metadata.get("step", 0)) + 1,
                active=active,
                graph_id=self.config.graph_id,
                tenant_id=self.config.tenant_id,
            )
        return GraphStateSnapshot(
            values=state.view(),
            next=tuple(active),
            config=new_config,
            metadata=dict(current.metadata),
            parent_config=config,
        )

    def get_state_history(
        self,
        config: Dict[str, Any],
        *,
        limit: Optional[int] = None,
    ) -> List[GraphStateSnapshot]:
        if self.checkpointer is None:
            return []
        if hasattr(self.checkpointer, "delta_channel_history"):
            delta = self.checkpointer.delta_channel_history(config)
            if delta:
                history = self.checkpointer.list_history(config, limit=limit)
                if history:
                    history[-1].metadata = {**history[-1].metadata, "channel_deltas": delta}
                return history
        return self.checkpointer.list_history(config, limit=limit)

    def invoke(self, input: Optional[Dict[str, Any]], /, **kwargs: Any) -> Dict[str, Any]:
        try:
            it = self._run_iter(input, kwargs, stream_mode=None)
            while True:
                next(it)
        except StopIteration as done:
            return done.value.values
        except GraphInterrupt as exc:
            out = {**exc.state, "__interrupt__": True, "__next__": sorted(exc.next_nodes)}
            if exc.payload is not None:
                out["__interrupt_payload__"] = exc.payload
            return out

    async def ainvoke(self, input: Optional[Dict[str, Any]], /, **kwargs: Any) -> Dict[str, Any]:
        try:
            async for _ in self._arun_iter(input, kwargs, stream_mode=None):
                pass
            assert self._last_run_result is not None
            return self._last_run_result.values
        except GraphInterrupt as exc:
            out = {**exc.state, "__interrupt__": True, "__next__": sorted(exc.next_nodes)}
            if exc.payload is not None:
                out["__interrupt_payload__"] = exc.payload
            return out

    def stream(self, input: Optional[Dict[str, Any]], /, **kwargs: Any) -> Iterator[Any]:
        stream_mode = kwargs.get("stream_mode", "values")
        try:
            yield from self._run_iter(input, kwargs, stream_mode=stream_mode)
        except GraphInterrupt:
            return

    async def astream(
        self, input: Optional[Dict[str, Any]], /, **kwargs: Any
    ) -> AsyncIterator[Any]:
        stream_mode = kwargs.get("stream_mode", "values")
        try:
            async for event in self._arun_iter(input, kwargs, stream_mode=stream_mode):
                yield event
                await asyncio.sleep(0)
        except GraphInterrupt:
            return

    def _resolve_config(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        cfg = kwargs.get("config") or {}
        if "configurable" not in cfg:
            cfg = {"configurable": {"thread_id": kwargs.get("thread_id", str(uuid4()))}}
        return cfg

    def _init_run(
        self,
        input: Optional[Dict[str, Any]],
        kwargs: Dict[str, Any],
    ) -> tuple[ChannelState, Set[str], int, RouteTracker, Dict[str, Any], bool]:
        config = self._resolve_config(kwargs)
        resume = input is None
        resume_value: Any = None
        if isinstance(input, dict) and "__resume__" in input:
            resume_value = input.get("__resume__")
            input = {k: v for k, v in input.items() if k != "__resume__"}
            if self.checkpointer is not None and self.checkpointer.get_tuple(config) is not None:
                resume = True
        super_step = 0
        active: Set[str] = set()

        if resume and self.checkpointer is not None:
            tup = self.checkpointer.get_tuple(config)
            if tup is None:
                raise ValueError("No checkpoint found for thread_id")
            state = state_from_checkpoint(tup.checkpoint)
            meta = tup.metadata or {}
            active = set(meta.get("active_nodes") or [])
            super_step = int(meta.get("step", 0))
            if resume_value is None:
                resume_value = meta.get("interrupt_resume")
            if not active and self.ir.entry:
                active = {self.ir.entry}
        else:
            state = ChannelState.from_input(input or {})
            active = {self.ir.entry} if self.ir.entry else set()

        self._resume_value = resume_value

        turn_id = state.view().get("turn_id") or state.view().get("request_id")
        tracker = RouteTracker(
            tenant_id=kwargs.get("tenant_id") or self.config.tenant_id,
            graph_id=kwargs.get("graph_id") or self.config.graph_id,
            sink=self.ledger_sink,
            turn_id=str(turn_id) if turn_id else None,
        )
        self._tracker = tracker
        self._llm_calls = 0
        return state, active, super_step, tracker, config, resume

    def _maybe_cache_skip(
        self,
        node_id: str,
        snapshot: ChannelState,
        super_step: int,
    ) -> Optional[Tuple[NodeUpdate, Optional[Any]]]:
        if self.cache_interceptor is None:
            return None
        result = self.cache_interceptor.try_skip(node_id, snapshot.view(), super_step=super_step)
        if result is None:
            return None
        update, decision = result
        return update, decision

    def _invoke_node(
        self,
        node_id: str,
        snapshot: ChannelState,
        super_step: int,
        *,
        on_emit: Optional[Any] = None,
    ) -> NodeUpdate:
        cached = self._maybe_cache_skip(node_id, snapshot, super_step)
        if cached is not None:
            return cached[0]
        ctx = NodeContext(
            state=snapshot,
            node_id=node_id,
            super_step=super_step,
            bus=self.bus,
            projector=self.projector,
            on_emit=on_emit,
            resume_value=getattr(self, "_resume_value", None),
        )
        fn = self.ir.nodes[node_id]
        update = fn(ctx)
        if getattr(fn, "_counts_as_llm", False):
            self._llm_calls += 1
        return update

    async def _ainvoke_node(
        self,
        node_id: str,
        snapshot: ChannelState,
        super_step: int,
        *,
        on_emit: Optional[Any] = None,
    ) -> NodeUpdate:
        cached = self._maybe_cache_skip(node_id, snapshot, super_step)
        if cached is not None:
            return cached[0]
        fn = self.ir.nodes[node_id]
        ctx = NodeContext(
            state=snapshot,
            node_id=node_id,
            super_step=super_step,
            bus=self.bus,
            projector=self.projector,
            on_emit=on_emit,
            resume_value=getattr(self, "_resume_value", None),
        )
        if inspect.iscoroutinefunction(fn):
            update = await fn(ctx)
        else:
            update = await asyncio.to_thread(fn, ctx)
        if getattr(fn, "_counts_as_llm", False):
            self._llm_calls += 1
        return update

    def _checkpoint(
        self,
        config: Dict[str, Any],
        state: ChannelState,
        *,
        super_step: int,
        active: Set[str],
        tracker: RouteTracker,
        metadata_extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        if self.checkpointer is None:
            return
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        self.checkpointer.put(
            config,
            state,
            super_step=super_step,
            active=active,
            graph_id=self.config.graph_id,
            tenant_id=self.config.tenant_id,
            metadata_extra=metadata_extra,
        )
        tracker.record_checkpoint(super_step=super_step, thread_id=thread_id)

    def _raise_dynamic_interrupt(
        self,
        *,
        interrupting_node: str,
        payload: Any,
        state: ChannelState,
        super_step: int,
        config: Dict[str, Any],
        tracker: RouteTracker,
        completed_nodes: Set[str],
        node_updates: List[Tuple[str, NodeUpdate, float, int, Optional[Any]]],
    ) -> None:
        next_active = {interrupting_node}
        for _done_id, update, _, _, _ in node_updates:
            state.apply(update)
        self._checkpoint(
            config,
            state,
            super_step=super_step + 1,
            active=next_active,
            tracker=tracker,
            metadata_extra={
                "interrupt_payload": payload,
                "interrupt_node": interrupting_node,
            },
        )
        tracker.record_interrupt(node=interrupting_node, super_step=super_step)
        self.last_tracker = tracker
        raise GraphInterrupt(
            state.view(),
            next_nodes=next_active,
            super_step=super_step,
            payload=payload,
        )

    def _check_interrupt(
        self,
        *,
        completed_nodes: Set[str],
        next_active: Set[str],
        state: ChannelState,
        super_step: int,
        config: Dict[str, Any],
        tracker: RouteTracker,
    ) -> None:
        halt_before = next_active & self.ir.interrupt_before
        halt_after = completed_nodes & self.ir.interrupt_after
        if not halt_before and not halt_after:
            return
        self._checkpoint(config, state, super_step=super_step, active=next_active, tracker=tracker)
        for node in sorted(halt_before | halt_after):
            tracker.record_interrupt(node=node, super_step=super_step)
        raise GraphInterrupt(state.view(), next_nodes=next_active, super_step=super_step)

    def _iter_write_events(
        self,
        state: ChannelState,
        node_updates: List[Tuple[str, NodeUpdate, float, int, Optional[Any]]],
        super_step: int,
        stream_mode: Optional[str],
        tracker: RouteTracker,
    ) -> Iterator[Any]:
        next_active: Set[str] = set()

        for node_id, update, _, duration_ms, cache_decision in node_updates:
            skipped = cache_decision is not None
            state.apply(update)
            freq = 0.0
            if update.primary:
                freq = self.bus.publish_envelope(node_id, update.primary)
                if self.transport is not None and self.transport.mode.value != "inproc":
                    self.transport.deliver_envelope(
                        envelope_id=str(update.primary.get("envelope_id") or ""),
                        vector_64=list(update.primary.get("vector") or []),
                        hop=node_id,
                        artifact_ref=str(update.primary.get("envelope_id") or ""),
                        from_hop=node_id,
                        to_hop="bus",
                    )

            view = state.view()
            route = self.ir.route_decision(node_id, view, update, self.bus)
            succs = set(route.targets)
            for succ in succs:
                next_active.add(succ)

            cache_hit = None
            cache_score = None
            if cache_decision is not None:
                cache_hit = cache_decision.is_hit
                cache_score = cache_decision.verify_score or cache_decision.coarse_score

            grounding = view.get("memory_confidence")
            grounding_score = float(grounding) if grounding is not None and node_id == "writer" else None

            tracker.record_step(
                node=node_id,
                edge_taken=next(iter(succs), None),
                route_via=route.route_via,
                rule_chain=list(
                    update.rule_chain
                    or (update.primary.get("rule_chain") if update.primary else [])
                    or []
                ),
                duration_ms=duration_ms,
                cache_hit=cache_hit,
                cache_score=cache_score,
                grounding_score=grounding_score,
                bus_frequency=freq,
                dominant_frequency=self.bus.dominant_frequency(),
                super_step=super_step,
                skipped=skipped,
            )

            if stream_mode == "debug":
                ts = datetime.now(timezone.utc).isoformat()
                yield {
                    "type": "task_result",
                    "timestamp": ts,
                    "payload": {
                        "name": node_id,
                        "result": {
                            **view,
                            "_bus_frequency": freq,
                            "_dominant_frequency": self.bus.dominant_frequency(),
                        },
                    },
                }
            elif stream_mode == "updates":
                yield {node_id: view}
            elif stream_mode == "messages" and update.primary:
                yield update.primary
            elif stream_mode == "values":
                yield view

        return next_active  # type: ignore[misc]

    def _super_step_gen(
        self,
        state: ChannelState,
        active: Set[str],
        super_step: int,
        *,
        stream_mode: Optional[str],
        tracker: RouteTracker,
        config: Dict[str, Any],
    ) -> Iterator[Any]:
        ordered = sorted(active)
        tracker.record_super_step(super_step, ordered)
        snapshot = state.snapshot()
        node_updates: List[Tuple[str, NodeUpdate, float, int, Optional[Any]]] = []
        pending_emits: List[Any] = []

        if stream_mode == "debug":
            for node_id in ordered:
                yield {
                    "type": "task",
                    "payload": {"name": node_id, "triggers": [f"branch:to:{node_id}"]},
                }

        def on_emit(chunk: Any) -> None:
            pending_emits.append(chunk)

        for node_id in ordered:
            while pending_emits:
                yield pending_emits.pop(0)
            started = time.perf_counter()
            cache_decision = None
            emit_cb = on_emit if stream_mode == "messages" else None
            if self.cache_interceptor is not None:
                cached = self.cache_interceptor.try_skip(node_id, snapshot.view(), super_step=super_step)
                if cached is not None:
                    update, cache_decision = cached
                else:
                    try:
                        update = self._invoke_node(node_id, snapshot, super_step, on_emit=emit_cb)
                    except NodeInterrupt as exc:
                        self._raise_dynamic_interrupt(
                            interrupting_node=node_id,
                            payload=exc.payload,
                            state=state,
                            super_step=super_step,
                            config=config,
                            tracker=tracker,
                            completed_nodes=set(),
                            node_updates=node_updates,
                        )
            else:
                try:
                    update = self._invoke_node(node_id, snapshot, super_step, on_emit=emit_cb)
                except NodeInterrupt as exc:
                    self._raise_dynamic_interrupt(
                        interrupting_node=node_id,
                        payload=exc.payload,
                        state=state,
                        super_step=super_step,
                        config=config,
                        tracker=tracker,
                        completed_nodes=set(),
                        node_updates=node_updates,
                    )
            while pending_emits:
                yield pending_emits.pop(0)
            duration_ms = int((time.perf_counter() - started) * 1000)
            node_updates.append((node_id, update, 0.0, duration_ms, cache_decision))

        write_gen = self._iter_write_events(
            state, node_updates, super_step, stream_mode, tracker
        )
        next_active: Set[str] = set()
        try:
            while True:
                yield next(write_gen)
        except StopIteration as done:
            next_active = done.value

        self._checkpoint(config, state, super_step=super_step + 1, active=next_active, tracker=tracker)
        self._check_interrupt(
            completed_nodes=set(ordered),
            next_active=next_active,
            state=state,
            super_step=super_step,
            config=config,
            tracker=tracker,
        )
        self._step_next_active = next_active

    async def _super_step_async_gen(
        self,
        state: ChannelState,
        active: Set[str],
        super_step: int,
        *,
        stream_mode: Optional[str],
        tracker: RouteTracker,
        config: Dict[str, Any],
    ) -> AsyncIterator[Any]:
        ordered = sorted(active)
        tracker.record_super_step(super_step, ordered)
        snapshot = state.snapshot()
        pending_emits: List[Any] = []

        if stream_mode == "debug":
            for node_id in ordered:
                yield {
                    "type": "task",
                    "payload": {"name": node_id, "triggers": [f"branch:to:{node_id}"]},
                }

        def on_emit(chunk: Any) -> None:
            pending_emits.append(chunk)

        async def run_one(node_id: str) -> Tuple[str, NodeUpdate, int, Optional[Any]]:
            started = time.perf_counter()
            cache_decision = None
            emit_cb = on_emit if stream_mode == "messages" else None
            if self.cache_interceptor is not None:
                cached = self.cache_interceptor.try_skip(node_id, snapshot.view(), super_step=super_step)
                if cached is not None:
                    update, cache_decision = cached
                else:
                    update = await self._ainvoke_node(node_id, snapshot, super_step, on_emit=emit_cb)
            else:
                update = await self._ainvoke_node(node_id, snapshot, super_step, on_emit=emit_cb)
            duration_ms = int((time.perf_counter() - started) * 1000)
            return node_id, update, duration_ms, cache_decision

        node_updates: List[Tuple[str, NodeUpdate, float, int, Optional[Any]]] = []
        for coro in asyncio.as_completed([run_one(n) for n in ordered]):
            node_id, update, duration_ms, cache_decision = await coro
            while pending_emits:
                yield pending_emits.pop(0)
            node_updates.append((node_id, update, 0.0, duration_ms, cache_decision))

        while pending_emits:
            yield pending_emits.pop(0)

        write_gen = self._iter_write_events(
            state, node_updates, super_step, stream_mode, tracker
        )
        next_active: Set[str] = set()
        try:
            while True:
                yield next(write_gen)
        except StopIteration as done:
            next_active = done.value

        self._checkpoint(config, state, super_step=super_step + 1, active=next_active, tracker=tracker)
        self._check_interrupt(
            completed_nodes=set(ordered),
            next_active=next_active,
            state=state,
            super_step=super_step,
            config=config,
            tracker=tracker,
        )
        self._step_next_active = next_active

    def _run_iter(
        self,
        input: Optional[Dict[str, Any]],
        kwargs: Dict[str, Any],
        *,
        stream_mode: Optional[str],
    ) -> Iterator[Any]:
        state, active, super_step, tracker, config, _ = self._init_run(input, kwargs)

        while active and super_step < self.config.recursion_limit:
            step_gen = self._super_step_gen(
                state,
                active,
                super_step,
                stream_mode=stream_mode,
                tracker=tracker,
                config=config,
            )
            try:
                while True:
                    if stream_mode is not None:
                        yield next(step_gen)
                    else:
                        next(step_gen)
            except StopIteration:
                active = self._step_next_active
            super_step += 1

        ledger = tracker.flush()
        self.last_ledger = ledger
        self.last_tracker = tracker
        result = RunResult(values=state.view(), events=[])
        self._last_run_result = result
        return result

    async def _arun_iter(
        self,
        input: Optional[Dict[str, Any]],
        kwargs: Dict[str, Any],
        *,
        stream_mode: Optional[str],
    ) -> AsyncIterator[Any]:
        state, active, super_step, tracker, config, _ = self._init_run(input, kwargs)

        while active and super_step < self.config.recursion_limit:
            step_gen = self._super_step_async_gen(
                state,
                active,
                super_step,
                stream_mode=stream_mode,
                tracker=tracker,
                config=config,
            )
            try:
                while True:
                    event = await step_gen.__anext__()
                    if stream_mode is not None:
                        yield event
            except StopAsyncIteration:
                active = self._step_next_active
            super_step += 1

        ledger = tracker.flush()
        self.last_ledger = ledger
        self.last_tracker = tracker
        self._last_run_result = RunResult(values=state.view(), events=[])


__all__ = ["CompiledGraph", "EngineConfig", "GraphInterrupt", "RunResult"]
