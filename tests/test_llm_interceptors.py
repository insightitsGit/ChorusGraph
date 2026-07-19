"""ADR-008 LLM interceptor tests."""

from __future__ import annotations

import pytest

from chorusgraph.core.constants import END, START
from chorusgraph.core.graph import Graph
from chorusgraph.core.intercept import InterceptDecision
from chorusgraph.core.channels import NodeUpdate
from chorusgraph.core.node import NodeContext, NodeInterrupt


def test_call_llm_proceed_and_counts():
    calls = {"n": 0}

    def model(s: str, u: str) -> str:
        calls["n"] += 1
        return f"ok:{u}"

    def gen(ctx: NodeContext) -> NodeUpdate:
        text = ctx.call_llm("sys", ctx.read().get("message", ""))
        return ctx.publish(artifact={"response": text}, category_slug="gen")

    g = Graph(tenant_id="ix")
    g.add_node("gen", gen)
    g.add_edge(START, "gen")
    g.add_edge("gen", END)
    compiled = g.compile().bind_llm(model)
    seen = {"before": 0, "after": 0}

    def before(ctx, state):
        seen["before"] += 1
        assert "user" in state
        return InterceptDecision.proceed()

    def after(ctx, state, out):
        seen["after"] += 1
        assert out.startswith("ok:")
        return InterceptDecision.proceed()

    compiled.register_interceptor(before_llm=before, after_llm=after)
    out = compiled.invoke({"message": "hi"})
    assert out["response"] == "ok:hi"
    assert calls["n"] == 1
    assert seen == {"before": 1, "after": 1}
    assert compiled._llm_calls >= 1


def test_before_llm_halt_raises_interrupt():
    def model(s: str, u: str) -> str:
        return "should-not-run"

    def gen(ctx: NodeContext) -> NodeUpdate:
        ctx.call_llm("sys", "q")
        return ctx.publish(artifact={"response": "x"}, category_slug="gen")

    g = Graph(tenant_id="ix")
    g.add_node("gen", gen)
    g.add_edge(START, "gen")
    g.add_edge("gen", END)
    compiled = g.compile().bind_llm(model)
    compiled.register_interceptor(
        before_llm=lambda ctx, state: InterceptDecision.halt(fallback="blocked"),
    )
    out = compiled.invoke({"message": "hi"})
    # invoke surfaces HITL / intercept halt as interrupt markers (not always raised)
    assert out.get("__interrupt__") is True
    payload = out.get("__interrupt_payload__") or {}
    assert payload.get("reason") == "llm_intercept_halt"
    assert payload.get("fallback") == "blocked"


def test_after_llm_halt_returns_fallback():
    def model(s: str, u: str) -> str:
        return "raw"

    def gen(ctx: NodeContext) -> NodeUpdate:
        text = ctx.call_llm("sys", "q")
        return ctx.publish(artifact={"response": text}, category_slug="gen")

    g = Graph(tenant_id="ix")
    g.add_node("gen", gen)
    g.add_edge(START, "gen")
    g.add_edge("gen", END)
    compiled = g.compile().bind_llm(model)
    compiled.register_interceptor(
        after_llm=lambda ctx, state, out: InterceptDecision.halt(fallback="safe"),
    )
    out = compiled.invoke({"message": "hi"})
    assert out["response"] == "safe"


def test_no_interceptor_inert():
    def model(s: str, u: str) -> str:
        return "plain"

    def gen(ctx: NodeContext) -> NodeUpdate:
        text = ctx.call_llm("sys", "q")
        return ctx.publish(artifact={"response": text}, category_slug="gen")

    g = Graph(tenant_id="ix")
    g.add_node("gen", gen)
    g.add_edge(START, "gen")
    g.add_edge("gen", END)
    out = g.compile().bind_llm(model).invoke({"message": "hi"})
    assert out["response"] == "plain"


def test_consumes_on_context():
    def gen(ctx: NodeContext) -> NodeUpdate:
        assert ctx.consumes == ["docs", "history"]
        return ctx.publish(artifact={"response": "ok"}, category_slug="gen")

    g = Graph(tenant_id="ix")
    g.add_node("gen", gen, consumes=["docs", "history"])
    g.add_edge(START, "gen")
    g.add_edge("gen", END)
    g.compile().invoke({"message": "hi"})


def test_before_llm_reroute_goto():
    def model(s: str, u: str) -> str:
        return "should-not-run"

    def gen(ctx: NodeContext) -> NodeUpdate:
        ctx.call_llm("sys", "q")
        return ctx.publish(artifact={"response": "from-gen"}, category_slug="gen")

    def alt(ctx: NodeContext) -> NodeUpdate:
        return ctx.publish(artifact={"response": "from-alt"}, category_slug="alt")

    g = Graph(tenant_id="ix")
    g.add_node("gen", gen)
    g.add_node("alt", alt)
    g.add_edge(START, "gen")
    # Declare alt as a legal Command/intercept goto target from gen.
    g.add_conditional_edges("gen", lambda _: "end", {"end": END, "alt": "alt"})
    g.add_edge("alt", END)
    compiled = g.compile().bind_llm(model)
    compiled.register_interceptor(
        before_llm=lambda ctx, state: InterceptDecision.reroute("alt"),
    )
    out = compiled.invoke({"message": "hi"})
    assert out["response"] == "from-alt"


def test_agent_with_interceptors_halt_before_tokens():
    from chorusgraph.agents.agent import Agent
    from chorusgraph.agents.policy import PlanPolicy, ReActOpts
    from chorusgraph.core.intercept import LlmInterceptHalt
    from chorusgraph.nodes.tool import ToolRegistry

    calls = {"n": 0}

    def model(s: str, u: str) -> str:
        calls["n"] += 1
        return '{"action":"finish","answer":"x"}'

    agent = Agent(
        pattern="react",
        tools=ToolRegistry(),
        model=model,
        policy=PlanPolicy(max_steps=2),
        pattern_opts=ReActOpts(max_tool_calls=2),
    ).with_interceptors(
        before_llm=lambda ctx, state: InterceptDecision.halt(fallback="blocked"),
    )
    with pytest.raises(LlmInterceptHalt) as exc:
        agent.run("hello")
    assert exc.value.fallback == "blocked"
    assert calls["n"] == 0
