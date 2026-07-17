"""ADR-006 L1 single-flight — coordinator + eligibility + graph miss join."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from chorusgraph.cache_gate.flight import (
    FlightPolicy,
    InProcessFlightCoordinator,
    flight_eligible,
)
from chorusgraph.cache_gate.sidecar import SidecarStore
from chorusgraph.compose.stack import ChorusStack
from chorusgraph.core.cache_interceptor import CacheRuntime
from chorusgraph.core.constants import END, START
from chorusgraph.core.graph import Graph
from chorusgraph.core.node import NodeContext
from chorusgraph.policy.embedder_guard import build_guarded_cache
from chorusgraph.sections.models import CachePolicy, CacheProfile


def test_flight_eligible_requires_opt_in_and_exact_shared_scope():
    profile = CacheProfile(keying="exact", scope="global", single_flight=False)
    assert not flight_eligible(
        profile,
        tenant_id="t",
        scope_id="global",
        category_slug="faq",
        query="hello",
        policy=FlightPolicy(enabled=False),
    ).eligible

    profile_on = CacheProfile(keying="exact", scope="global", single_flight=True)
    ok = flight_eligible(
        profile_on,
        tenant_id="t",
        scope_id="global",
        category_slug="faq",
        query="Hello  there",
        policy=FlightPolicy(enabled=False),
    )
    assert ok.eligible
    assert ok.flight_key

    # Same normalized query → same key
    ok2 = flight_eligible(
        profile_on,
        tenant_id="t",
        scope_id="global",
        category_slug="faq",
        query="hello there",
        policy=FlightPolicy(enabled=True),
    )
    assert ok.flight_key == ok2.flight_key


def test_flight_not_eligible_for_semantic_or_user_scope():
    sem = CacheProfile(keying="semantic", scope="global", single_flight=True)
    assert not flight_eligible(
        sem,
        tenant_id="t",
        scope_id="global",
        category_slug="fx",
        query="usd eur",
        policy=FlightPolicy(enabled=True),
    ).eligible

    user = CacheProfile(keying="exact", scope="user", single_flight=True)
    assert not flight_eligible(
        user,
        tenant_id="t",
        scope_id="user:a",
        category_slug="faq",
        query="hello",
        policy=FlightPolicy(enabled=True),
    ).eligible


def test_coordinator_followers_join_leader():
    coord = InProcessFlightCoordinator()
    calls = {"n": 0}
    barrier = threading.Barrier(2)

    def compute():
        calls["n"] += 1
        time.sleep(0.15)
        return {"answer": calls["n"]}

    results = []

    def worker():
        barrier.wait()
        results.append(coord.run("k1", compute, timeout_s=2.0))

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(worker)
        f2 = pool.submit(worker)
        f1.result()
        f2.result()

    assert calls["n"] == 1
    assert results[0] == results[1] == {"answer": 1}


def test_coordinator_timeout_fallthrough():
    coord = InProcessFlightCoordinator()
    gate = threading.Event()

    def leader_compute():
        gate.set()
        time.sleep(0.4)
        return "L"

    def follower_compute():
        return "F"

    def follow():
        gate.wait(timeout=1.0)
        return coord.run("t", follower_compute, timeout_s=0.05)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fl = pool.submit(lambda: coord.run("t", leader_compute, timeout_s=2.0))
        time.sleep(0.05)  # ensure leader registered
        ff = pool.submit(follow)
        assert fl.result() == "L"
        assert ff.result() == "F"  # timed out → own compute


def test_coordinator_error_fallthrough():
    coord = InProcessFlightCoordinator()
    started = threading.Event()

    def boom():
        started.set()
        time.sleep(0.05)
        raise RuntimeError("leader failed")

    def ok():
        return "recovered"

    def follow():
        started.wait(timeout=1.0)
        time.sleep(0.02)
        return coord.run("err", ok, timeout_s=1.0, on_leader_error="fallthrough")

    with ThreadPoolExecutor(max_workers=2) as pool:
        fl = pool.submit(lambda: coord.run("err", boom, timeout_s=1.0))
        ff = pool.submit(follow)
        with pytest.raises(RuntimeError):
            fl.result()
        assert ff.result() == "recovered"


def test_default_runtime_flight_disabled_no_join():
    """Default CacheRuntime must not coalesce (preserve existing miss parallelism)."""
    cache = build_guarded_cache("flight-default-off")
    sidecar = SidecarStore(":memory:")
    runtime = CacheRuntime(cache=cache, sidecar=sidecar)
    assert runtime.flight_policy.enabled is False

    from chorusgraph.core.cache_interceptor import CacheInterceptor, NodeCacheSpec

    interceptor = CacheInterceptor(
        runtime,
        {
            "n": NodeCacheSpec(
                node_id="n",
                cache_policy=CachePolicy.EXACT,
                profile=CacheProfile(keying="exact", scope="global"),
            )
        },
    )
    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        time.sleep(0.1)
        return calls["n"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(interceptor.run_miss, "n", {"message": "same"}, compute)
        f2 = pool.submit(interceptor.run_miss, "n", {"message": "same"}, compute)
        f1.result()
        f2.result()
    assert calls["n"] == 2


def test_graph_single_flight_joins_concurrent_invokes():
    calls = {"n": 0}
    lock = threading.Lock()

    def work(ctx: NodeContext):
        with lock:
            calls["n"] += 1
        time.sleep(0.2)
        return ctx.publish(artifact={"response": "ok", "n": calls["n"]}, category_slug="faq")

    g = Graph(tenant_id="flight-demo")
    g.add_node(
        "work",
        work,
        category_slug="faq",
        cache_policy=CachePolicy.EXACT,
        cache_profile=CacheProfile(keying="exact", scope="global", single_flight=True),
    )
    g.add_edge(START, "work")
    g.add_edge("work", END)

    stack = ChorusStack.defaults(tenant_id="flight-demo", enable_memory=False)
    compiled = g.compile(stack=stack)

    def run_once():
        return compiled.invoke({"message": "What is ChorusGraph?"})

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(run_once)
        b = pool.submit(run_once)
        a.result()
        b.result()

    assert calls["n"] == 1


def test_stack_with_flight_enables_runtime_policy():
    stack = ChorusStack.defaults(tenant_id="f").with_flight(FlightPolicy(enabled=True, join_timeout_s=5.0))
    rt = stack.to_cache_runtime()
    assert rt.flight_policy.enabled is True
    assert rt.flight_policy.join_timeout_s == 5.0
