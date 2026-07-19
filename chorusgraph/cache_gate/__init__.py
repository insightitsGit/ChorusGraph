"""Two-stage cache gate — wraps real PrismCache, shadow-safe."""

from chorusgraph.cache_gate.backend import recall, recall_direct, seed_cache_entry
from chorusgraph.cache_gate.decision import Decision, DecisionKind
from chorusgraph.cache_gate.flight import FlightPolicy, InProcessFlightCoordinator, flight_eligible
from chorusgraph.cache_gate.gate import gate
from chorusgraph.cache_gate.scope import normalize_exact_query, scope_id
from chorusgraph.cache_gate.seed_policy import is_refusal_response, safety_approving, should_seed_cache
from chorusgraph.cache_gate.sidecar import SidecarStore


def mark_revalidate(
    sidecar: SidecarStore,
    *,
    packet_ids=None,
    query_vector=None,
    threshold: float = 0.55,
) -> int:
    """Public helper — mark cache-gate entries for force refresh on next hit."""
    return sidecar.mark_revalidate(
        packet_ids,
        query_vector=query_vector,
        threshold=threshold,
    )


__all__ = [
    "Decision",
    "DecisionKind",
    "FlightPolicy",
    "InProcessFlightCoordinator",
    "SidecarStore",
    "flight_eligible",
    "gate",
    "is_refusal_response",
    "mark_revalidate",
    "normalize_exact_query",
    "recall",
    "recall_direct",
    "safety_approving",
    "scope_id",
    "seed_cache_entry",
    "should_seed_cache",
]
