"""Resonance frequency bus — prismresonance InProcessBroadcast / RedisBroadcast."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from prismresonance import FrequencyFamily, InProcessBroadcast

from chorusgraph.core.envelope import PrismEnvelopeLike

try:
    from prismresonance import RedisBroadcast as _RedisBroadcast
except ImportError:  # pragma: no cover
    _RedisBroadcast = None  # type: ignore[misc, assignment]

# Map common route/category slugs to priority bands for deterministic routing.
SLUG_FREQUENCY: Dict[str, float] = {
    "general": FrequencyFamily.NORMAL.value,
    "greeting": FrequencyFamily.NORMAL.value,
    "short_path": FrequencyFamily.NORMAL.value,
    "long_path": FrequencyFamily.ALERT.value,
    "emergency": FrequencyFamily.EMERGENCY.value,
    "archive": FrequencyFamily.ARCHIVE.value,
}


def frequency_for_slug(category_slug: str) -> float:
    slug = (category_slug or "general").strip().lower()
    if slug in SLUG_FREQUENCY:
        return SLUG_FREQUENCY[slug]
    digest = hashlib.sha256(slug.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 5
    families = [
        FrequencyFamily.NEUTRAL,
        FrequencyFamily.NORMAL,
        FrequencyFamily.ALERT,
        FrequencyFamily.RECOVERY,
        FrequencyFamily.ARCHIVE,
    ]
    return families[bucket].value


class ResonanceBus:
    """
    L0 coordination layer (ENGINE §2.2).

    ``InProcessBroadcast`` carries operational *frequencies* across agents;
    envelope payloads live in ``ChannelState``. After each publish we align
    the bus to the envelope's ``category_slug`` frequency.

    Use ``backend='redis'`` for multi-process cluster coordination (P5).
    """

    def __init__(self, *, backend: str = "inproc", redis_url: Optional[str] = None) -> None:
        if backend == "redis":
            if _RedisBroadcast is None:
                raise ImportError("RedisBroadcast requires prismresonance with Redis support")
            self._bus: Any = _RedisBroadcast(redis_url or "redis://localhost:6379/0")
        else:
            self._bus = InProcessBroadcast()
        self._listen: Dict[str, float] = {}
        self._backend = backend

    def register_node(self, node_id: str, *, category_slug: str = "general") -> None:
        freq = frequency_for_slug(category_slug)
        self._listen[node_id] = freq
        self._bus.register_agent(node_id, freq)

    def publish_envelope(self, node_id: str, envelope: PrismEnvelopeLike) -> float:
        slug = str(envelope.get("category_slug") or "general")
        freq = frequency_for_slug(slug)
        self._bus.set_frequency(node_id, freq)
        self._bus.broadcast(freq)
        return freq

    def dominant_frequency(self) -> float:
        return self._bus.dominant_frequency()

    def subscribers_for_slug(self, category_slug: str) -> List[str]:
        target = frequency_for_slug(category_slug)
        nearest = FrequencyFamily.nearest(target)
        out: List[str] = []
        for node_id, listen in self._listen.items():
            if FrequencyFamily.nearest(listen) == nearest:
                out.append(node_id)
        return out

    def frequencies(self) -> Dict[str, float]:
        return self._bus.get_frequencies()


__all__ = ["ResonanceBus", "frequency_for_slug"]
