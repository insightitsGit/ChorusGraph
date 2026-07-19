"""Node execution context — envelope-native API."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

from prismlang import PrismProjector

from chorusgraph.core.bus import ResonanceBus
from chorusgraph.core.channels import ChannelState, NodeUpdate, publish_update
from chorusgraph.core.envelope import compact_json

NodeFn = Callable[["NodeContext"], Union["NodeUpdate", "Command"]]


@dataclass
class Command:
    """LangGraph-compatible node return — state update plus optional routing override."""

    update: Optional[Dict[str, Any] | NodeUpdate] = None
    goto: Optional[str | List[str]] = None


class NodeInterrupt(Exception):
    """Raised when a node calls ``NodeContext.interrupt()`` mid-execution."""

    def __init__(self, payload: Any) -> None:
        self.payload = payload
        super().__init__(f"Node interrupt: {payload!r}")


def native_node(fn: NodeFn) -> NodeFn:
    """Mark an envelope-native node handler."""
    fn._chorusgraph_native = True  # type: ignore[attr-defined]
    return fn


def is_native_node(fn: Callable[..., Any]) -> bool:
    if getattr(fn, "_chorusgraph_native", False):
        return True
    sig = inspect.signature(fn)
    params = list(sig.parameters.values())
    if not params:
        return False
    ret = sig.return_annotation
    if ret is NodeUpdate or ret == NodeUpdate or getattr(ret, "__name__", "") == "NodeUpdate":
        return True
    if isinstance(ret, str) and "NodeUpdate" in ret:
        return True
    ann = params[0].annotation
    if ann is NodeContext or getattr(ann, "__name__", "") == "NodeContext":
        return True
    if isinstance(ann, str) and "NodeContext" in ann:
        return True
    return False


@dataclass
class NodeContext:
    """Read-only channel view + publish helpers for one node invocation."""

    state: ChannelState
    node_id: str
    super_step: int
    bus: ResonanceBus
    projector: Optional[PrismProjector] = None
    on_emit: Optional[Callable[[Any], None]] = field(default=None, repr=False)
    resume_value: Any = None
    branch_id: Optional[str] = None
    branch_payload: Optional[Dict[str, Any]] = None
    run_config: Optional[Dict[str, Any]] = None
    parent_run_id: Optional[str] = None
    # ADR-008 / PrismShine — optional provider-boundary hooks (inert when unset).
    llm_callable: Optional[Callable[[str, str], str]] = field(default=None, repr=False)
    before_llm: Optional[Callable[..., Any]] = field(default=None, repr=False)
    after_llm: Optional[Callable[..., Any]] = field(default=None, repr=False)
    consumes: Optional[List[str]] = None
    llm_calls_made: int = field(default=0, repr=False)

    def read(self) -> Dict[str, Any]:
        view = self.state.view()
        if self.branch_payload:
            return {**view, **self.branch_payload}
        return view

    def emit(self, chunk: Any) -> None:
        """Push a token/chunk into the live ``messages`` stream (if streaming)."""
        if self.on_emit is not None:
            self.on_emit(chunk)

    def interrupt(self, payload: Any) -> Any:
        """Halt mid-node; on resume the same call returns the human-provided value."""
        if self.resume_value is not None:
            return self.resume_value
        raise NodeInterrupt(payload)

    def call_llm(self, system: str, user: str, *, model: Optional[Callable[[str, str], str]] = None) -> str:
        """
        Provider-boundary LLM call (ADR-008).

        Fires ``before_llm`` / ``after_llm`` interceptors registered on the compiled
        graph. Prefer this over calling a raw model so PrismShine can halt before tokens.
        """
        from chorusgraph.core.intercept import run_llm_with_interceptors

        llm = model or self.llm_callable
        if llm is None:
            raise ValueError(
                "NodeContext.call_llm requires a model= callable or ctx.llm_callable"
            )
        out = run_llm_with_interceptors(
            ctx=self,
            system=system,
            user=user,
            model=llm,
            before_llm=self.before_llm,
            after_llm=self.after_llm,
        )
        self.llm_calls_made += 1
        return out

    def publish(
        self,
        *,
        artifact: Dict[str, Any],
        category_slug: Optional[str] = None,
        rule_chain: Optional[list[str]] = None,
    ) -> NodeUpdate:
        text = artifact.get("raw_output") or compact_json(artifact)
        if self.projector is None:
            slug = category_slug or "general"
            vector = [0.0] * 64
            chain = list(rule_chain or [])
        else:
            slug, vec, proj_rules = self.projector.project(text if str(text).strip() else "[no output]")
            vector = vec.tolist()
            if rule_chain is not None:
                chain = list(rule_chain)
            else:
                chain = list(proj_rules)
            if category_slug:
                slug = category_slug

        return publish_update(
            hop=self.node_id,
            artifact=artifact,
            vector=vector,
            category_slug=slug,
            rule_chain=chain + ([f"branch:{self.branch_id}"] if self.branch_id else []),
            turn_id=self.super_step,
        )


def dict_node_adapter(
    fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    *,
    hop: str,
    category_slug_from: str = "hop",
) -> NodeFn:
    """
    Temporary bridge for dict-style nodes — wraps output as a single envelope.

    Prefer native ``NodeFn`` returning ``NodeUpdate`` for new graphs.

    By default the Resonance ``category_slug`` is the node id (``hop``), not ``route``.
    Router nodes often write ``route`` into shared state; downstream dict nodes still
    carry that key in their result dict. Using ``route`` as the slug makes unrelated
    nodes publish on the same frequency (e.g. every node after ``classify_intent`` all
    tuning to ``site_kb``). Pass ``category_slug_from="route"`` only if you explicitly
    want the legacy behavior.
    """

    def _envelope_item(raw: Any) -> Dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if hasattr(raw, "__dataclass_fields__"):
            from dataclasses import asdict

            return asdict(raw)
        return {
            "envelope_id": getattr(raw, "envelope_id", None),
            "vector": list(getattr(raw, "vector", []) or []),
            "agent_id": getattr(raw, "agent_id", hop),
            "category_slug": getattr(raw, "category_slug", "general"),
            "rule_chain": list(getattr(raw, "rule_chain", []) or []),
            "turn_id": getattr(raw, "turn_id", 0),
        }

    def wrapped(ctx: NodeContext) -> NodeUpdate:
        result = fn(ctx.read())
        artifact = dict(result)
        raw = artifact.pop("prism_sequence", None)
        artifact.pop("rule_chain", None)
        hop_metrics = artifact.get("hop_metrics")
        if hop_metrics:
            from dataclasses import asdict

            artifact["hop_metrics"] = [
                asdict(m) if hasattr(m, "__dataclass_fields__") else m for m in hop_metrics
            ]
        if category_slug_from == "route":
            slug = str(result.get("route") or result.get("category_slug") or hop)
        else:
            slug = str(result.get("category_slug") or hop)
        update = ctx.publish(
            artifact=artifact,
            rule_chain=list(result.get("rule_chain") or []),
            category_slug=slug,
        )
        if raw:
            update.envelopes.extend(_envelope_item(env) for env in raw)
        return update

    return wrapped


__all__ = ["Command", "NodeContext", "NodeFn", "NodeInterrupt", "dict_node_adapter", "is_native_node", "native_node"]
