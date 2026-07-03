"""Bulk-synchronous scheduler — the Prism engine (ENGINE §3.1, P1–P4)."""

from __future__ import annotations

import asyncio
import inspect
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union
from uuid import uuid4

from prismlang import PrismProjector

from chorusgraph.core.bus import ResonanceBus
from chorusgraph.core.cache_interceptor import CacheInterceptor
from chorusgraph.core.channels import ChannelState, NodeUpdate
from chorusgraph.core.ir import GraphIR
from chorusgraph.core.node import Command, NodeContext, NodeInterrupt
from chorusgraph.core.persistence import EngineCheckpointer, GraphStateSnapshot, state_from_checkpoint
from chorusgraph.core.pending_writes import MidStepAbort
from chorusgraph.core.send import (
    COARSE_DEDUP_THRESHOLD,
    Send,
    SendBatch,
    dedup_sends,
    join_satisfied,
)
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
    max_branches: int = 64
    clock_ms: Callable[[], float] = field(default_factory=lambda: (lambda: time.perf_counter() * 1000.0))


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
    stack: Optional[Any] = None
    _native: bool = True

    last_ledger: Optional[Any] = None
    last_tracker: Optional[RouteTracker] = None
    _tracker: Optional[RouteTracker] = field(default=None, repr=False)
    _llm_calls: int = field(default=0, repr=False)
    _last_run_result: Optional[RunResult] = field(default=None, repr=False)
    _step_next_active: Set[str] = field(default_factory=set, repr=False)
    _step_in_progress: bool = field(default=False, repr=False)
    _send_batch: Optional[SendBatch] = field(default=None, repr=False)
    _straggler_batch: Optional[SendBatch] = field(default=None, repr=False)

    @staticmethod
    def _branch_pending_id(target: str, branch_id: str) -> str:
        safe = branch_id.replace("|", "__").replace(":", "_")
        return f"{target}__{safe}"

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
        except MidStepAbort as exc:
            return {**exc.state, "__mid_step_abort__": True}

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
        except MidStepAbort as exc:
            return {**exc.state, "__mid_step_abort__": True}

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
            if meta.get("step_in_progress") and meta.get("pending_super_step") is not None:
                super_step = int(meta["pending_super_step"])
                self._step_in_progress = True
            else:
                super_step = int(meta.get("step", 0))
                self._step_in_progress = False
            if resume_value is None:
                resume_value = meta.get("interrupt_resume")
            pending_batch = meta.get("pending_send_batch")
            if pending_batch:
                self._send_batch = self._send_batch_from_metadata(pending_batch)
                active = set()
                pending_writes = self.checkpointer.get_pending_writes(config, super_step)
                for task in self._send_batch.tasks:
                    if task.branch_id in self._send_batch.completed:
                        continue
                    pending_id = self._branch_pending_id(task.target, task.branch_id)
                    if pending_id in pending_writes:
                        update = pending_writes[pending_id]
                        self._send_batch.completed[task.branch_id] = update
                        self._fan_back_branch_result(self._send_batch, task, update)
                for bid in meta.get("pending_send_batch", {}).get("completed") or []:
                    if bid not in self._send_batch.completed:
                        pw = self.checkpointer.get_pending_writes(config, super_step)
                        task = next((t for t in self._send_batch.tasks if t.branch_id == bid), None)
                        if task:
                            pending_id = self._branch_pending_id(task.target, task.branch_id)
                            if pending_id in pw:
                                update = pw[pending_id]
                                self._send_batch.completed[bid] = update
                                self._fan_back_branch_result(self._send_batch, task, update)
            if not active and self.ir.entry and not meta.get("step_in_progress"):
                active = {self.ir.entry}
        else:
            state = ChannelState.from_input(input or {})
            active = {self.ir.entry} if self.ir.entry else set()
            self._step_in_progress = False

        self._resume_value = resume_value
        self._parent_run_id = kwargs.get("_parent_run_id")
        self._subgraph_node = kwargs.get("_subgraph_node")

        turn_id = state.view().get("turn_id") or state.view().get("request_id")
        tracker = RouteTracker(
            tenant_id=kwargs.get("tenant_id") or self.config.tenant_id,
            graph_id=kwargs.get("graph_id") or self.config.graph_id,
            sink=self.ledger_sink,
            turn_id=str(turn_id) if turn_id else None,
            parent_run_id=self._parent_run_id,
            subgraph_node=self._subgraph_node,
        )
        self._tracker = tracker
        self._llm_calls = 0
        return state, active, super_step, tracker, config, resume

    def _maybe_cache_skip(
        self,
        node_id: str,
        snapshot: ChannelState,
        super_step: int,
        *,
        view: Optional[Dict[str, Any]] = None,
    ) -> Optional[Tuple[NodeUpdate, Optional[Any]]]:
        if self.cache_interceptor is None:
            return None
        result = self.cache_interceptor.try_skip(
            node_id, view if view is not None else snapshot.view(), super_step=super_step
        )
        if result is None:
            return None
        update, decision = result
        return update, decision

    def _coerce_node_result(
        self,
        ctx: NodeContext,
        raw: Any,
    ) -> Tuple[NodeUpdate, Optional[frozenset[str]], Optional[List[Send]]]:
        command_goto: Optional[frozenset[str]] = None
        sends: Optional[List[Send]] = None
        if isinstance(raw, list) and raw and all(isinstance(x, Send) for x in raw):
            return NodeUpdate(), None, list(raw)
        if isinstance(raw, Command):
            if raw.goto is not None:
                goto_items = raw.goto if isinstance(raw.goto, list) else [raw.goto]
                if goto_items and all(isinstance(x, Send) for x in goto_items):
                    sends = list(goto_items)
                else:
                    command_goto = self.ir.validate_command_goto(ctx.node_id, raw.goto)
            if raw.update is None:
                return NodeUpdate(), command_goto, sends
            if isinstance(raw.update, NodeUpdate):
                return raw.update, command_goto, sends
            slug = str(raw.update.get("category_slug") or raw.update.get("route") or ctx.node_id)
            return ctx.publish(
                artifact=dict(raw.update),
                category_slug=slug,
                rule_chain=list(raw.update.get("rule_chain") or []),
            ), command_goto, sends
        if not isinstance(raw, NodeUpdate):
            raise TypeError(
                f"Node {ctx.node_id!r} must return NodeUpdate, Command, Send list, got {type(raw)}"
            )
        return raw, None, None

    def _invoke_node(
        self,
        node_id: str,
        snapshot: ChannelState,
        super_step: int,
        *,
        on_emit: Optional[Any] = None,
        branch_id: Optional[str] = None,
        branch_payload: Optional[Dict[str, Any]] = None,
    ) -> Tuple[NodeUpdate, Optional[frozenset[str]], Optional[List[Send]]]:
        branch_view = (
            {**snapshot.view(), **branch_payload} if branch_payload else None
        )
        cached = self._maybe_cache_skip(
            node_id, snapshot, super_step, view=branch_view
        )
        if cached is not None:
            return cached[0], None, None
        ctx = NodeContext(
            state=snapshot,
            node_id=node_id,
            super_step=super_step,
            bus=self.bus,
            projector=self.projector,
            on_emit=on_emit,
            resume_value=getattr(self, "_resume_value", None),
            branch_id=branch_id,
            branch_payload=branch_payload,
            run_config=getattr(self, "_run_config", None),
            parent_run_id=getattr(self, "_parent_run_id", None),
        )
        fn = self.ir.nodes[node_id]
        raw = fn(ctx)
        if getattr(fn, "_counts_as_llm", False):
            self._llm_calls += 1
        return self._coerce_node_result(ctx, raw)

    async def _ainvoke_node(
        self,
        node_id: str,
        snapshot: ChannelState,
        super_step: int,
        *,
        on_emit: Optional[Any] = None,
        branch_id: Optional[str] = None,
        branch_payload: Optional[Dict[str, Any]] = None,
    ) -> Tuple[NodeUpdate, Optional[frozenset[str]], Optional[List[Send]]]:
        branch_view = (
            {**snapshot.view(), **branch_payload} if branch_payload else None
        )
        cached = self._maybe_cache_skip(
            node_id, snapshot, super_step, view=branch_view
        )
        if cached is not None:
            return cached[0], None, None
        fn = self.ir.nodes[node_id]
        ctx = NodeContext(
            state=snapshot,
            node_id=node_id,
            super_step=super_step,
            bus=self.bus,
            projector=self.projector,
            on_emit=on_emit,
            resume_value=getattr(self, "_resume_value", None),
            branch_id=branch_id,
            branch_payload=branch_payload,
            run_config=getattr(self, "_run_config", None),
            parent_run_id=getattr(self, "_parent_run_id", None),
        )
        if inspect.iscoroutinefunction(fn):
            raw = await fn(ctx)
        else:
            raw = await asyncio.to_thread(fn, ctx)
        if getattr(fn, "_counts_as_llm", False):
            self._llm_calls += 1
        return self._coerce_node_result(ctx, raw)

    def _checkpoint(
        self,
        config: Dict[str, Any],
        state: ChannelState,
        *,
        super_step: int,
        active: Set[str],
        tracker: RouteTracker,
        metadata_extra: Optional[Dict[str, Any]] = None,
        clear_pending_for_step: Optional[int] = None,
    ) -> None:
        if self.checkpointer is None:
            return
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        extra = dict(metadata_extra or {})
        if clear_pending_for_step is not None:
            self.checkpointer.clear_pending_writes(config, clear_pending_for_step)
            extra.setdefault("step_in_progress", False)
        self.checkpointer.put(
            config,
            state,
            super_step=super_step,
            active=active,
            graph_id=self.config.graph_id,
            tenant_id=self.config.tenant_id,
            metadata_extra=extra or None,
        )
        tracker.record_checkpoint(super_step=super_step, thread_id=thread_id)

    def _persist_pending_write(
        self,
        config: Dict[str, Any],
        super_step: int,
        node_id: str,
        update: NodeUpdate,
    ) -> None:
        if self.checkpointer is None:
            return
        self.checkpointer.put_writes(config, super_step, node_id, update)

    def _load_pending_writes(
        self,
        config: Dict[str, Any],
        super_step: int,
    ) -> Dict[str, NodeUpdate]:
        if self.checkpointer is None:
            return {}
        return self.checkpointer.get_pending_writes(config, super_step)

    def _checkpoint_mid_step(
        self,
        *,
        config: Dict[str, Any],
        state: ChannelState,
        super_step: int,
        active: Set[str],
        tracker: RouteTracker,
    ) -> None:
        if self.checkpointer is None:
            return
        self._checkpoint(
            config,
            state,
            super_step=super_step,
            active=active,
            tracker=tracker,
            metadata_extra={
                "step_in_progress": True,
                "pending_super_step": super_step,
            },
        )

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
        node_updates: List[
            Tuple[str, NodeUpdate, float, int, Optional[Any], Optional[frozenset[str]], Optional[List[Send]]]
        ],
    ) -> None:
        next_active = {interrupting_node}
        for _done_id, update, _, _, _, _, _ in node_updates:
            state.apply(update)
        for node_id, update, _, _, _, _, _ in node_updates:
            self._persist_pending_write(config, super_step, node_id, update)
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

    def _send_batch_to_metadata(self, batch: SendBatch) -> Dict[str, Any]:
        join_spec = batch.join_spec
        if isinstance(join_spec, tuple):
            join_spec_meta: Any = list(join_spec)
        else:
            join_spec_meta = join_spec
        return {
            "send_node": batch.send_node,
            "super_step": batch.super_step,
            "join_node": batch.join_node,
            "join_spec": join_spec_meta,
            "branches_requested": batch.branches_requested,
            "branches_executed": batch.branches_executed,
            "send_to_task": batch.send_to_task,
            "tasks": [
                {
                    "branch_id": t.branch_id,
                    "target": t.target,
                    "payload": t.payload,
                    "request_indices": t.request_indices,
                }
                for t in batch.tasks
            ],
            "completed": list(batch.completed.keys()),
            "join_activated": batch.join_activated,
            "branch_start_ms": batch.branch_start_ms,
            "parent_snapshot": batch.parent_snapshot.to_checkpoint_values() if batch.parent_snapshot else None,
        }

    def _send_batch_from_metadata(self, meta: Dict[str, Any]) -> SendBatch:
        from chorusgraph.core.send import BranchTask

        join_spec = meta.get("join_spec", "all")
        if isinstance(join_spec, list):
            join_spec = tuple(join_spec)
        tasks = [
            BranchTask(
                branch_id=t["branch_id"],
                target=t["target"],
                payload=dict(t["payload"]),
                request_indices=list(t["request_indices"]),
            )
            for t in meta.get("tasks") or []
        ]
        batch = SendBatch(
            send_node=str(meta["send_node"]),
            super_step=int(meta.get("super_step") or 0),
            tasks=tasks,
            send_to_task=list(meta.get("send_to_task") or []),
            join_node=str(meta["join_node"]),
            join_spec=join_spec,
            branches_requested=int(meta.get("branches_requested") or 0),
            branches_executed=int(meta.get("branches_executed") or 0),
            fan_results=[None] * int(meta.get("branches_requested") or 0),
            join_activated=bool(meta.get("join_activated")),
            branch_start_ms=float(meta.get("branch_start_ms") or 0.0),
            parent_snapshot=(
                ChannelState.from_checkpoint_values(meta["parent_snapshot"])
                if meta.get("parent_snapshot")
                else None
            ),
        )
        for bid in meta.get("completed") or []:
            batch.resumed_branch_ids.add(str(bid))
        return batch

    def _execute_remote_send_batch(
        self,
        state: ChannelState,
        batch: SendBatch,
        super_step: int,
        *,
        stream_mode: Optional[str],
        tracker: RouteTracker,
        config: Dict[str, Any],
    ) -> Iterator[Any]:
        from chorusgraph.core.subgraph_transport import invoke_remote_send_batch

        spec = batch.remote_subgraph_spec
        assert spec is not None
        cache = None
        if self.cache_interceptor is not None:
            cache = self.cache_interceptor._runtime.cache
        parent_run_id = config.get("_parent_run_id")
        remote_handler = getattr(self.transport, "remote_batch_handler", None) if self.transport else None
        started = time.perf_counter()
        from chorusgraph.core.send import join_threshold

        limit = join_threshold(batch.join_spec, batch.branches_executed)
        tasks_to_run = batch.tasks[:limit]
        outputs = invoke_remote_send_batch(
            spec,
            tasks_to_run,
            config=config,
            transport=self.transport,
            parent_run_id=parent_run_id,
            cache=cache,
            remote_executor=remote_handler,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        for task, artifact in zip(tasks_to_run, outputs):
            update = batch.completed.get(task.branch_id)
            if update is None:
                from chorusgraph.core.channels import publish_update

                update = publish_update(
                    hop=task.target,
                    artifact=dict(artifact),
                    vector=[0.0] * 64,
                    category_slug="general",
                    rule_chain=[f"remote_send:{spec.location}"],
                    turn_id=super_step,
                )
            batch.completed[task.branch_id] = update
            self._fan_back_branch_result(batch, task, update)
            tracker.record_step(
                node=task.target,
                edge_taken=batch.join_node,
                route_via=f"remote_{spec.location}",
                rule_chain=list(update.rule_chain or []),
                duration_ms=duration_ms,
                super_step=super_step,
            )
        batch.remote_executed = True
        batch.remote_branch_outputs = [dict(a) for a in outputs]
        self._apply_send_batch_to_state(state, batch)
        batch.join_activated = True
        if stream_mode == "values":
            yield state.view()
        self._step_next_active = {batch.join_node}

    async def _execute_remote_send_batch_async(
        self,
        state: ChannelState,
        batch: SendBatch,
        super_step: int,
        *,
        stream_mode: Optional[str],
        tracker: RouteTracker,
        config: Dict[str, Any],
    ) -> AsyncIterator[Any]:
        for item in self._execute_remote_send_batch(
            state,
            batch,
            super_step,
            stream_mode=stream_mode,
            tracker=tracker,
            config=config,
        ):
            yield item

    def _schedule_send_batch(
        self,
        *,
        send_node: str,
        sends: List[Send],
        super_step: int,
        tracker: RouteTracker,
        state: Optional[ChannelState] = None,
    ) -> None:
        if len(sends) > self.config.max_branches:
            raise ValueError(
                f"Send fan-out from {send_node!r} requested {len(sends)} branches "
                f"(max_branches={self.config.max_branches})"
            )
        for send in sends:
            if send.target not in self.ir.nodes:
                raise KeyError(f"Send target {send.target!r} is not a registered node")
        join_node, join_spec = self.ir.resolve_join_for_branch_target(sends[0].target)
        cache = None
        if self.cache_interceptor is not None:
            cache = self.cache_interceptor._runtime.cache
        tasks, send_to_task = dedup_sends(
            sends,
            send_node=send_node,
            super_step=super_step,
            cache=cache,
            coarse_threshold=COARSE_DEDUP_THRESHOLD,
        )
        tracker.record_send_batch(
            send_node=send_node,
            super_step=super_step,
            branches_requested=len(sends),
            branches_executed=len(tasks),
        )
        remote_spec = None
        target_fn = self.ir.nodes.get(sends[0].target)
        if target_fn is not None:
            remote_spec = getattr(target_fn, "_subgraph_spec", None)
            if remote_spec is not None and getattr(remote_spec, "location", "local") == "local":
                remote_spec = None
        self._send_batch = SendBatch(
            send_node=send_node,
            super_step=super_step,
            tasks=sorted(tasks, key=lambda t: t.branch_id),
            send_to_task=send_to_task,
            join_node=join_node,
            join_spec=join_spec,
            branches_requested=len(sends),
            branches_executed=len(tasks),
            fan_results=[None] * len(sends),
            branch_start_ms=self.config.clock_ms(),
            parent_snapshot=state.snapshot() if state is not None else None,
            remote_subgraph_spec=remote_spec,
        )

    def _fan_back_branch_result(self, batch: SendBatch, task: Any, update: NodeUpdate) -> None:
        artifact = {}
        if update.primary:
            eid = str(update.primary.get("envelope_id") or "")
            artifact = dict(update.artifacts.get(eid) or update.primary)
        elif update.artifacts:
            artifact = dict(next(iter(update.artifacts.values())))
        artifact = {**artifact, "branch_id": task.branch_id}
        for req_idx in task.request_indices:
            batch.fan_results[req_idx] = dict(artifact)

    def _apply_send_batch_to_state(self, state: ChannelState, batch: SendBatch) -> None:
        if batch.remote_branch_outputs is not None:
            state._scalars["branch_outputs"] = list(batch.remote_branch_outputs)
            return
        outputs = [dict(r) if r is not None else {} for r in batch.fan_results]
        state._scalars["branch_outputs"] = outputs

    def _branch_super_step_gen(
        self,
        state: ChannelState,
        batch: SendBatch,
        super_step: int,
        *,
        stream_mode: Optional[str],
        tracker: RouteTracker,
        config: Dict[str, Any],
    ) -> Iterator[Any]:
        pending = [t for t in batch.tasks if t.branch_id not in batch.completed]
        if not pending:
            return
        if batch.remote_subgraph_spec is not None and not batch.remote_executed:
            yield from self._execute_remote_send_batch(
                state,
                batch,
                super_step,
                stream_mode=stream_mode,
                tracker=tracker,
                config=config,
            )
            return
        snapshot = batch.parent_snapshot if batch.parent_snapshot is not None else state.snapshot()
        pending_writes = self._load_pending_writes(config, super_step)
        task = sorted(pending, key=lambda t: t.branch_id)[0]
        pending_id = self._branch_pending_id(task.target, task.branch_id)
        tracker.record_super_step(super_step, [pending_id])

        started = time.perf_counter()
        if pending_id in pending_writes:
            update = pending_writes[pending_id]
        elif task.branch_id in batch.resumed_branch_ids:
            if pending_id not in pending_writes:
                return
            update = pending_writes[pending_id]
        else:
            try:
                update, _, sends = self._invoke_node(
                    task.target,
                    snapshot,
                    super_step,
                    branch_id=task.branch_id,
                    branch_payload=task.payload,
                )
            except NodeInterrupt as exc:
                self._raise_dynamic_interrupt(
                    interrupting_node=task.target,
                    payload=exc.payload,
                    state=state,
                    super_step=super_step,
                    config=config,
                    tracker=tracker,
                    completed_nodes=set(),
                    node_updates=[],
                )
            except MidStepAbort as exc:
                self._checkpoint(
                    config,
                    state,
                    super_step=super_step,
                    active=set(),
                    tracker=tracker,
                    metadata_extra={
                        "step_in_progress": True,
                        "pending_super_step": super_step,
                        "pending_send_batch": self._send_batch_to_metadata(batch),
                    },
                )
                raise MidStepAbort(
                    snapshot.view(),
                    super_step=super_step,
                    active_nodes=set(),
                ) from exc
            if sends:
                raise ValueError(f"Branch node {task.target!r} cannot emit Send inside a branch")
            self._persist_pending_write(config, super_step, pending_id, update)
        duration_ms = int((time.perf_counter() - started) * 1000)
        batch.completed[task.branch_id] = update
        self._fan_back_branch_result(batch, task, update)
        state.apply(update)
        tracker.record_step(
            node=task.target,
            edge_taken=batch.join_node,
            route_via="send",
            rule_chain=list(update.rule_chain or []),
            duration_ms=duration_ms,
            super_step=super_step,
        )
        if stream_mode == "values":
            yield state.view()

        elapsed = self.config.clock_ms() - batch.branch_start_ms
        completed_count = len(batch.completed)
        if not batch.join_activated and join_satisfied(
            batch.join_spec,
            completed=completed_count,
            total=batch.branches_executed,
            elapsed_ms=elapsed,
        ):
            batch.join_activated = True
            self._apply_send_batch_to_state(state, batch)

        all_done = completed_count >= batch.branches_executed
        if all_done:
            self._apply_send_batch_to_state(state, batch)

        next_active: Set[str] = set()
        if batch.join_activated:
            next_active.add(batch.join_node)

        self._checkpoint(
            config,
            state,
            super_step=super_step + 1,
            active=next_active,
            tracker=tracker,
            clear_pending_for_step=super_step if all_done else None,
        )
        self._step_next_active = next_active

    async def _branch_super_step_async_gen(
        self,
        state: ChannelState,
        batch: SendBatch,
        super_step: int,
        *,
        stream_mode: Optional[str],
        tracker: RouteTracker,
        config: Dict[str, Any],
    ) -> AsyncIterator[Any]:
        pending = [t for t in batch.tasks if t.branch_id not in batch.completed]
        if not pending:
            return
        if batch.remote_subgraph_spec is not None and not batch.remote_executed:
            async for item in self._execute_remote_send_batch_async(
                state,
                batch,
                super_step,
                stream_mode=stream_mode,
                tracker=tracker,
                config=config,
            ):
                yield item
            return
        snapshot = batch.parent_snapshot if batch.parent_snapshot is not None else state.snapshot()
        pending_writes = self._load_pending_writes(config, super_step)
        task = sorted(pending, key=lambda t: t.branch_id)[0]
        pending_id = self._branch_pending_id(task.target, task.branch_id)
        tracker.record_super_step(super_step, [pending_id])

        started = time.perf_counter()
        if pending_id in pending_writes:
            update = pending_writes[pending_id]
        elif task.branch_id in batch.resumed_branch_ids:
            if pending_id not in pending_writes:
                return
            update = pending_writes[pending_id]
        else:
            update, _, sends = await self._ainvoke_node(
                task.target,
                snapshot,
                super_step,
                branch_id=task.branch_id,
                branch_payload=task.payload,
            )
            if sends:
                raise ValueError(f"Branch node {task.target!r} cannot emit Send inside a branch")
            self._persist_pending_write(config, super_step, pending_id, update)
        duration_ms = int((time.perf_counter() - started) * 1000)
        batch.completed[task.branch_id] = update
        self._fan_back_branch_result(batch, task, update)
        state.apply(update)
        tracker.record_step(
            node=task.target,
            edge_taken=batch.join_node,
            route_via="send",
            rule_chain=list(update.rule_chain or []),
            duration_ms=duration_ms,
            super_step=super_step,
        )
        if stream_mode == "values":
            yield state.view()

        elapsed = self.config.clock_ms() - batch.branch_start_ms
        completed_count = len(batch.completed)
        if not batch.join_activated and join_satisfied(
            batch.join_spec,
            completed=completed_count,
            total=batch.branches_executed,
            elapsed_ms=elapsed,
        ):
            batch.join_activated = True
            self._apply_send_batch_to_state(state, batch)

        all_done = completed_count >= batch.branches_executed
        if all_done:
            self._apply_send_batch_to_state(state, batch)

        next_active: Set[str] = set()
        if batch.join_activated:
            next_active.add(batch.join_node)

        self._checkpoint(
            config,
            state,
            super_step=super_step + 1,
            active=next_active,
            tracker=tracker,
            clear_pending_for_step=super_step if all_done else None,
        )
        self._step_next_active = next_active

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
        node_updates: List[
            Tuple[str, NodeUpdate, float, int, Optional[Any], Optional[frozenset[str]], Optional[List[Send]]]
        ],
        super_step: int,
        stream_mode: Optional[str],
        tracker: RouteTracker,
    ) -> Iterator[Any]:
        next_active: Set[str] = set()

        for node_id, update, _, duration_ms, cache_decision, command_goto, sends in node_updates:
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
            route_via: Optional[str] = None
            if sends:
                self._schedule_send_batch(
                    send_node=node_id,
                    sends=sends,
                    super_step=super_step,
                    tracker=tracker,
                    state=state,
                )
                succs: Set[str] = set()
            elif command_goto is not None:
                succs = set(command_goto)
                route_via = "command"
            else:
                route = self.ir.route_decision(node_id, view, update, self.bus)
                succs = set(route.targets)
                route_via = route.route_via
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
                route_via=route_via,
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
        node_updates: List[
            Tuple[str, NodeUpdate, float, int, Optional[Any], Optional[frozenset[str]], Optional[List[Send]]]
        ] = []
        pending_emits: List[Any] = []
        pending_writes = self._load_pending_writes(config, super_step)

        if stream_mode == "debug":
            for node_id in ordered:
                yield {
                    "type": "task",
                    "payload": {"name": node_id, "triggers": [f"branch:to:{node_id}"]},
                }

        def on_emit(chunk: Any) -> None:
            pending_emits.append(chunk)

        try:
            for node_id in ordered:
                while pending_emits:
                    yield pending_emits.pop(0)
                started = time.perf_counter()
                cache_decision = None
                emit_cb = on_emit if stream_mode == "messages" else None
                command_goto: Optional[frozenset[str]] = None
                sends: Optional[List[Send]] = None
                if node_id in pending_writes:
                    update = pending_writes[node_id]
                elif self.cache_interceptor is not None:
                    cached = self.cache_interceptor.try_skip(node_id, snapshot.view(), super_step=super_step)
                    if cached is not None:
                        update, cache_decision = cached
                    else:
                        try:
                            update, command_goto, sends = self._invoke_node(
                                node_id, snapshot, super_step, on_emit=emit_cb
                            )
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
                    if node_id not in pending_writes:
                        self._persist_pending_write(config, super_step, node_id, update)
                else:
                    try:
                        update, command_goto, sends = self._invoke_node(
                            node_id, snapshot, super_step, on_emit=emit_cb
                        )
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
                    self._persist_pending_write(config, super_step, node_id, update)
                while pending_emits:
                    yield pending_emits.pop(0)
                duration_ms = int((time.perf_counter() - started) * 1000)
                node_updates.append(
                    (node_id, update, 0.0, duration_ms, cache_decision, command_goto, sends)
                )
        except MidStepAbort as exc:
            self._checkpoint_mid_step(
                config=config,
                state=snapshot,
                super_step=super_step,
                active=set(ordered),
                tracker=tracker,
            )
            raise MidStepAbort(
                snapshot.view(),
                super_step=super_step,
                active_nodes=set(ordered),
            ) from exc

        write_gen = self._iter_write_events(
            state, node_updates, super_step, stream_mode, tracker
        )
        next_active: Set[str] = set()
        try:
            while True:
                yield next(write_gen)
        except StopIteration as done:
            next_active = done.value

        self._checkpoint(
            config,
            state,
            super_step=super_step + 1,
            active=next_active,
            tracker=tracker,
            clear_pending_for_step=super_step,
        )
        self._step_in_progress = False
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
        pending_writes = self._load_pending_writes(config, super_step)

        if stream_mode == "debug":
            for node_id in ordered:
                yield {
                    "type": "task",
                    "payload": {"name": node_id, "triggers": [f"branch:to:{node_id}"]},
                }

        def on_emit(chunk: Any) -> None:
            pending_emits.append(chunk)

        async def run_one(node_id: str) -> Tuple[str, NodeUpdate, int, Optional[Any], Optional[frozenset[str]], Optional[List[Send]]]:
            started = time.perf_counter()
            cache_decision = None
            command_goto: Optional[frozenset[str]] = None
            sends: Optional[List[Send]] = None
            emit_cb = on_emit if stream_mode == "messages" else None
            if node_id in pending_writes:
                update = pending_writes[node_id]
            elif self.cache_interceptor is not None:
                cached = self.cache_interceptor.try_skip(node_id, snapshot.view(), super_step=super_step)
                if cached is not None:
                    update, cache_decision = cached
                else:
                    update, command_goto, sends = await self._ainvoke_node(
                        node_id, snapshot, super_step, on_emit=emit_cb
                    )
                if node_id not in pending_writes:
                    self._persist_pending_write(config, super_step, node_id, update)
            else:
                update, command_goto, sends = await self._ainvoke_node(
                    node_id, snapshot, super_step, on_emit=emit_cb
                )
                self._persist_pending_write(config, super_step, node_id, update)
            duration_ms = int((time.perf_counter() - started) * 1000)
            return node_id, update, duration_ms, cache_decision, command_goto, sends

        node_updates: List[
            Tuple[str, NodeUpdate, float, int, Optional[Any], Optional[frozenset[str]], Optional[List[Send]]]
        ] = []
        try:
            for coro in asyncio.as_completed([run_one(n) for n in ordered]):
                node_id, update, duration_ms, cache_decision, command_goto, sends = await coro
                while pending_emits:
                    yield pending_emits.pop(0)
                node_updates.append(
                    (node_id, update, 0.0, duration_ms, cache_decision, command_goto, sends)
                )
        except MidStepAbort as exc:
            self._checkpoint_mid_step(
                config=config,
                state=snapshot,
                super_step=super_step,
                active=set(ordered),
                tracker=tracker,
            )
            raise MidStepAbort(
                snapshot.view(),
                super_step=super_step,
                active_nodes=set(ordered),
            ) from exc

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

        self._checkpoint(
            config,
            state,
            super_step=super_step + 1,
            active=next_active,
            tracker=tracker,
            clear_pending_for_step=super_step,
        )
        self._step_in_progress = False
        self._check_interrupt(
            completed_nodes=set(ordered),
            next_active=next_active,
            state=state,
            super_step=super_step,
            config=config,
            tracker=tracker,
        )
        self._step_next_active = next_active

    def _drain_branch_steps(
        self,
        state: ChannelState,
        *,
        super_step: int,
        stream_mode: Optional[str],
        tracker: RouteTracker,
        config: Dict[str, Any],
    ) -> Tuple[int, Set[str]]:
        """Run pending Send branches; return (updated super_step, active join nodes)."""
        active: Set[str] = set()
        step = super_step
        batch = self._send_batch
        while batch is not None and len(batch.completed) < batch.branches_executed:
            step_gen = self._branch_super_step_gen(
                state, batch, step, stream_mode=stream_mode, tracker=tracker, config=config
            )
            try:
                while True:
                    if stream_mode is not None:
                        next(step_gen)
                    else:
                        next(step_gen)
            except MidStepAbort:
                raise
            except StopIteration:
                pass
            step += 1
            if batch.join_activated:
                active = {batch.join_node}
                if len(batch.completed) < batch.branches_executed:
                    self._straggler_batch = batch
                self._send_batch = None
                break
        if batch is not None and len(batch.completed) >= batch.branches_executed:
            active = {batch.join_node}
            self._send_batch = None
        return step, active

    async def _adrain_branch_steps(
        self,
        state: ChannelState,
        *,
        super_step: int,
        stream_mode: Optional[str],
        tracker: RouteTracker,
        config: Dict[str, Any],
    ) -> Tuple[int, Set[str]]:
        active: Set[str] = set()
        step = super_step
        batch = self._send_batch
        while batch is not None and len(batch.completed) < batch.branches_executed:
            step_gen = self._branch_super_step_async_gen(
                state, batch, step, stream_mode=stream_mode, tracker=tracker, config=config
            )
            try:
                async for _ in step_gen:
                    if stream_mode is not None:
                        pass
            except StopAsyncIteration:
                pass
            step += 1
            if batch.join_activated:
                active = set(self._step_next_active)
                if len(batch.completed) < batch.branches_executed:
                    self._straggler_batch = batch
                self._send_batch = None
                break
        if batch is not None and len(batch.completed) >= batch.branches_executed:
            active = {batch.join_node}
            self._send_batch = None
        return step, active

    def _finish_stragglers(
        self,
        state: ChannelState,
        *,
        super_step: int,
        stream_mode: Optional[str],
        tracker: RouteTracker,
        config: Dict[str, Any],
    ) -> int:
        batch = self._straggler_batch
        step = super_step
        while batch is not None and len(batch.completed) < batch.branches_executed:
            step_gen = self._branch_super_step_gen(
                state, batch, step, stream_mode=stream_mode, tracker=tracker, config=config
            )
            try:
                while True:
                    if stream_mode is not None:
                        next(step_gen)
                    else:
                        next(step_gen)
            except StopIteration:
                pass
            step += 1
        if batch is not None:
            self._apply_send_batch_to_state(state, batch)
            self._straggler_batch = None
        return step

    def _run_iter(
        self,
        input: Optional[Dict[str, Any]],
        kwargs: Dict[str, Any],
        *,
        stream_mode: Optional[str],
    ) -> Iterator[Any]:
        state, active, super_step, tracker, config, _ = self._init_run(input, kwargs)
        self._run_config = config

        while (active or self._send_batch) and super_step < self.config.recursion_limit:
            if active and self._send_batch is None:
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
            if self._send_batch is not None:
                try:
                    super_step, branch_active = self._drain_branch_steps(
                        state,
                        super_step=super_step,
                        stream_mode=stream_mode,
                        tracker=tracker,
                        config=config,
                    )
                except MidStepAbort:
                    raise
                if branch_active:
                    active = branch_active
            super_step += 1

        if self._straggler_batch is not None:
            super_step = self._finish_stragglers(
                state,
                super_step=super_step,
                stream_mode=stream_mode,
                tracker=tracker,
                config=config,
            )

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
        self._run_config = config

        while (active or self._send_batch) and super_step < self.config.recursion_limit:
            if active and self._send_batch is None:
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
            if self._send_batch is not None:
                super_step, branch_active = await self._adrain_branch_steps(
                    state,
                    super_step=super_step,
                    stream_mode=stream_mode,
                    tracker=tracker,
                    config=config,
                )
                if branch_active:
                    active = branch_active
            super_step += 1

        if self._straggler_batch is not None:
            super_step = self._finish_stragglers(
                state,
                super_step=super_step,
                stream_mode=stream_mode,
                tracker=tracker,
                config=config,
            )

        ledger = tracker.flush()
        self.last_ledger = ledger
        self.last_tracker = tracker
        self._last_run_result = RunResult(values=state.view(), events=[])


__all__ = ["CompiledGraph", "EngineConfig", "GraphInterrupt", "RunResult"]
