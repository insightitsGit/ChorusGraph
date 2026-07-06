"""Two-stage cache gate — wraps real PrismCache, shadow-safe."""

from chorusgraph.cache_gate.backend import recall, recall_direct, seed_cache_entry
from chorusgraph.cache_gate.decision import Decision, DecisionKind
from chorusgraph.cache_gate.gate import gate
from chorusgraph.cache_gate.scope import normalize_exact_query, scope_id
from chorusgraph.cache_gate.seed_policy import is_refusal_response, safety_approving, should_seed_cache
from chorusgraph.cache_gate.sidecar import SidecarStore

__all__ = [
    "Decision",
    "DecisionKind",
    "SidecarStore",
    "gate",
    "is_refusal_response",
    "normalize_exact_query",
    "recall",
    "recall_direct",
    "safety_approving",
    "scope_id",
    "seed_cache_entry",
    "should_seed_cache",
]
