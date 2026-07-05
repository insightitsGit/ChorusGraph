"""E2 resilience — fault injection, breakers, partial results."""

from __future__ import annotations

import pytest

from chorusgraph.core import END, START, Graph
from chorusgraph.core.channels import NodeUpdate
from chorusgraph.core.node import NodeContext
from chorusgraph.ledger.sink import SqliteLedgerSink
from chorusgraph.memory.async_digest import AsyncDigester
from chorusgraph.nodes.tool import ToolSpec, run_tool
from chorusgraph.resilience import (
    CallPolicy,
    ChorusExternalError,
    ErrorKind,
    IdempotencyGuard,
    RetryPolicy,
    classify_exception,
    reset_breakers,
    resilient_call,
)
from chorusgraph.resilience.circuit_breaker import BreakerConfig, get_breaker


@pytest.fixture(autouse=True)
def _reset_breakers():
    reset_breakers()
    yield
    reset_breakers()


def test_classify_timeout_as_transient():
    detail = classify_exception(TimeoutError("slow"), service="frankfurter")
    assert detail.kind == ErrorKind.TRANSIENT
    assert detail.retryable


def test_resilient_call_retries_then_succeeds():
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("temporary")
        return "ok"

    out = resilient_call(
        "test-flaky",
        flaky,
        policy=CallPolicy(
            timeout_seconds=2.0, retry=RetryPolicy(max_retries=3, base_delay_seconds=0.01)
        ),
    )
    assert out == "ok"
    assert calls["n"] == 3


def test_circuit_breaker_opens_after_failures():
    breaker = get_breaker(
        "test-open", BreakerConfig(failure_threshold=2, recovery_timeout_seconds=60.0)
    )
    policy = CallPolicy(timeout_seconds=1.0, retry=RetryPolicy(max_retries=0))

    def always_fail() -> None:
        raise ConnectionError("down")

    for _ in range(2):
        with pytest.raises(ChorusExternalError):
            resilient_call("test-open", always_fail, policy=policy)

    with pytest.raises(ChorusExternalError) as exc:
        resilient_call("test-open", always_fail, policy=policy)
    assert exc.value.detail.code == "circuit_open"


def test_run_tool_fault_injection_returns_clean_failure():
    def broken_tool(**_kwargs):
        raise ConnectionError("Frankfurter unreachable")

    spec = ToolSpec(
        name="broken_fx",
        description="fault injection",
        parameters={},
        fn=broken_tool,
        timeout_seconds=1.0,
        max_retries=1,
    )
    result = run_tool(spec, from_currency="USD", to_currency="EUR")
    assert not result.ok
    assert result.error
    assert result.attempts >= 2


def test_graph_survives_node_failure_with_typed_ledger_error():
    def ok(ctx: NodeContext) -> NodeUpdate:
        return ctx.publish(artifact={"seed": 1}, category_slug="general")

    def boom(_ctx: NodeContext) -> NodeUpdate:
        raise RuntimeError("simulated LLM outage")

    graph = Graph(graph_id="resilience-test")
    graph.add_node("ok", ok)
    graph.add_node("boom", boom)
    graph.add_edge(START, "ok")
    graph.add_edge("ok", "boom")
    graph.add_edge("boom", END)

    sink = SqliteLedgerSink(":memory:")
    compiled = graph.compile()
    compiled.attach_ledger(sink=sink, graph_id="resilience-test")
    result = compiled.invoke({"seed": 0})

    assert result.get("seed") == 1
    assert result.get("__partial__") is True
    assert "__node_error__" in result
    assert compiled.last_ledger is not None
    failed = [s for s in compiled.last_ledger.steps if s.error_code]
    assert failed
    assert failed[-1].error_kind in ("transient", "permanent")
    assert failed[-1].node == "boom"


def test_idempotency_guard_prevents_duplicate_digest():
    calls = {"n": 0}

    def memory_factory():
        class Mem:
            def digest(self, text, *, source_id, agent_id):
                calls["n"] += 1
                from prismcortex.models import DigestOutcome, DigestResult

                return DigestResult(outcome=DigestOutcome.STAGED, reason="ok")

            def sleep(self):
                return 0

        return Mem()

    guard = IdempotencyGuard()
    digester = AsyncDigester(memory_factory, idempotency=guard)
    digester.submit_digest("hello", source_id="turn-1", agent_id="agent")
    digester.submit_digest("hello", source_id="turn-1", agent_id="agent")
    digester.wait_idle(timeout=5.0)
    assert calls["n"] == 1
