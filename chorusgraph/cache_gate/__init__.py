"""Two-stage cache gate — wraps real PrismCache, shadow-safe."""

from chorusgraph.cache_gate.backend import recall, seed_cache_entry
from chorusgraph.cache_gate.decision import Decision, DecisionKind
from chorusgraph.cache_gate.gate import gate
from chorusgraph.cache_gate.sidecar import SidecarStore

__all__ = [
    "Decision",
    "DecisionKind",
    "SidecarStore",
    "gate",
    "recall",
    "seed_cache_entry",
]
