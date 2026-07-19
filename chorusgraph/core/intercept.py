"""LLM call interceptors — provider-boundary hooks for PrismShine (ADR-008)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Literal, Mapping, Optional

InterceptAction = Literal["proceed", "halt", "reroute"]

BeforeLlmHook = Callable[["NodeContext", Mapping[str, Any]], "InterceptDecision"]
AfterLlmHook = Callable[["NodeContext", Mapping[str, Any], Any], "InterceptDecision"]


@dataclass(frozen=True)
class InterceptDecision:
    """Outcome of a before_llm / after_llm hook."""

    action: InterceptAction = "proceed"
    fallback: Any = None
    hop: Optional[str] = None

    @classmethod
    def proceed(cls) -> "InterceptDecision":
        return cls(action="proceed")

    @classmethod
    def halt(cls, fallback: Any = None) -> "InterceptDecision":
        return cls(action="halt", fallback=fallback)

    @classmethod
    def reroute(cls, hop: str) -> "InterceptDecision":
        return cls(action="reroute", hop=hop)


class LlmInterceptHalt(Exception):
    """Raised when before/after_llm returns halt — maps to NodeInterrupt."""

    def __init__(self, fallback: Any = None) -> None:
        self.fallback = fallback
        super().__init__("LLM intercept halt")


class LlmInterceptReroute(Exception):
    """Raised when before/after_llm requests a hop reroute."""

    def __init__(self, hop: str) -> None:
        self.hop = hop
        super().__init__(f"LLM intercept reroute → {hop}")


@dataclass
class InterceptorRegistry:
    """Optional hooks registered on CompiledGraph (inert when empty)."""

    before_llm: Optional[BeforeLlmHook] = None
    after_llm: Optional[AfterLlmHook] = None

    def clear(self) -> None:
        self.before_llm = None
        self.after_llm = None


def wrap_llm_callable(
    model: Callable[[str, str], str],
    *,
    before_llm: Optional[BeforeLlmHook] = None,
    after_llm: Optional[AfterLlmHook] = None,
    context_factory: Optional[Callable[[], tuple[Any, Mapping[str, Any]]]] = None,
) -> Callable[[str, str], str]:
    """
    Wrap a ``(system, user) -> str`` model so interceptors fire at the provider boundary.

    ``context_factory`` returns ``(NodeContext|None, state_mapping)``. When context is
    None, hooks receive a lightweight stand-in and still see state.
    """

    def wrapped(system: str, user: str) -> str:
        ctx: Any = None
        state: Mapping[str, Any] = {"system": system, "user": user}
        if context_factory is not None:
            ctx, state = context_factory()
            state = dict(state)
            state.setdefault("system", system)
            state.setdefault("user", user)
        if ctx is None:
            # Agent / bare-model path — duck-typed shim so hooks still fire.
            class _Shim:
                def read(self) -> Dict[str, Any]:
                    return dict(state)

            ctx = _Shim()
        if before_llm is not None:
            decision = before_llm(ctx, state)
            _apply_decision(decision)
        out = model(system, user)
        if after_llm is not None:
            decision = after_llm(ctx, state, out)
            _apply_decision(decision, output=out)
            if decision.action == "halt" and decision.fallback is not None:
                return decision.fallback
        return out

    return wrapped


def _apply_decision(decision: InterceptDecision, *, output: Any = None) -> None:
    if decision.action == "proceed":
        return
    if decision.action == "halt":
        raise LlmInterceptHalt(decision.fallback)
    if decision.action == "reroute":
        if not decision.hop:
            raise ValueError("InterceptDecision.reroute requires hop")
        raise LlmInterceptReroute(decision.hop)


def run_llm_with_interceptors(
    *,
    ctx: Any,
    system: str,
    user: str,
    model: Callable[[str, str], str],
    before_llm: Optional[BeforeLlmHook] = None,
    after_llm: Optional[AfterLlmHook] = None,
) -> str:
    """Provider-boundary call used by ``NodeContext.call_llm``."""
    from chorusgraph.core.node import NodeInterrupt

    state = ctx.read() if hasattr(ctx, "read") else {}
    state = dict(state)
    state["system"] = system
    state["user"] = user
    try:
        if before_llm is not None:
            decision = before_llm(ctx, state)
            if decision.action == "halt":
                raise NodeInterrupt(
                    {"reason": "llm_intercept_halt", "fallback": decision.fallback}
                )
            if decision.action == "reroute":
                raise LlmInterceptReroute(decision.hop or "")
        out = model(system, user)
        if after_llm is not None:
            decision = after_llm(ctx, state, out)
            if decision.action == "halt":
                if decision.fallback is not None:
                    return decision.fallback
                raise NodeInterrupt(
                    {"reason": "llm_intercept_halt", "fallback": decision.fallback}
                )
            if decision.action == "reroute":
                raise LlmInterceptReroute(decision.hop or "")
        return out
    except LlmInterceptHalt as exc:
        raise NodeInterrupt({"reason": "llm_intercept_halt", "fallback": exc.fallback}) from exc


__all__ = [
    "AfterLlmHook",
    "BeforeLlmHook",
    "InterceptDecision",
    "InterceptorRegistry",
    "LlmInterceptHalt",
    "LlmInterceptReroute",
    "run_llm_with_interceptors",
    "wrap_llm_callable",
]
