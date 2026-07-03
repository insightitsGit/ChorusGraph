"""T5 — RedisBroadcast two-process bus tests."""

from __future__ import annotations

import multiprocessing as mp
import os
import time

import pytest

from chorusgraph.core.bus import ResonanceBus, frequency_for_slug


def _redis_url() -> str | None:
    return os.environ.get("CHORUSGRAPH_REDIS_URL")


def _redis_reachable(url: str) -> bool:
    try:
        import redis

        client = redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
        return True
    except Exception:
        return False


@pytest.mark.skipif(
    _redis_url() is None or not _redis_reachable(_redis_url() or ""),
    reason="CHORUSGRAPH_REDIS_URL unset or Redis unreachable — skip (no fake)",
)
def test_redis_broadcast_two_process_visibility():
    url = _redis_url()
    assert url is not None

    ready = mp.Event()
    seen = mp.Value("d", 0.0)

    def worker(node_id: str, slug: str) -> None:
        bus = ResonanceBus(backend="redis", redis_url=url)
        bus.register_node(node_id, category_slug=slug)
        ready.set()
        time.sleep(0.5)
        freq = frequency_for_slug(slug)
        bus._bus.set_frequency(node_id, freq)
        bus._bus.broadcast(freq)
        time.sleep(0.5)
        dom = bus.dominant_frequency()
        with seen.get_lock():
            if dom == freq:
                seen.value = dom

    p1 = mp.Process(target=worker, args=("agent-a", "emergency"))
    p2 = mp.Process(target=worker, args=("agent-b", "general"))
    p1.start()
    p2.start()
    p1.join(timeout=15)
    p2.join(timeout=15)
    if p1.is_alive():
        p1.terminate()
    if p2.is_alive():
        p2.terminate()
    assert p1.exitcode == 0, "worker p1 failed — is Redis reachable at CHORUSGRAPH_REDIS_URL?"
    assert p2.exitcode == 0
    assert seen.value == frequency_for_slug("emergency")


def test_inproc_routing_deterministic():
    bus = ResonanceBus(backend="inproc")
    bus.register_node("a", category_slug="general")
    bus.register_node("b", category_slug="emergency")
    env = {"category_slug": "emergency", "envelope_id": "e1", "vector": [0.0] * 64}
    bus.publish_envelope("a", env)
    subs = bus.subscribers_for_slug("emergency")
    assert "b" in subs
