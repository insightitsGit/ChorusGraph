"""T4 — Quality-gated cache seeding."""

from __future__ import annotations

from chorusgraph.cache_gate.seed_policy import (
    is_refusal_response,
    safety_approving,
    should_seed_cache,
)


def test_refusal_blocks_seed():
    ok, reason = should_seed_cache(
        response="Cannot provide a recommendation without an upstream safety verdict.",
        abstained=False,
    )
    assert not ok
    assert reason == "refusal_response"


def test_abstain_blocks_seed():
    ok, reason = should_seed_cache(response="ok", abstained=True)
    assert not ok
    assert reason == "abstained"


def test_safety_required_for_high_risk():
    ok, _ = should_seed_cache(
        response="Recommend aspirin.",
        safety_verdict={"verdict": "ABSTAIN"},
        require_safety=True,
    )
    assert not ok
    ok2, reason2 = should_seed_cache(
        response="Recommend aspirin with citation.",
        safety_verdict={"verdict": "APPROVED"},
        require_safety=True,
    )
    assert ok2
    assert reason2 == "ok"


def test_is_refusal_patterns():
    assert is_refusal_response("Safety verdict is missing.")
    assert not is_refusal_response("Recommend warfarin with bleeding risk counseling.")


def test_safety_approving_text():
    assert safety_approving("APPROVED with citations")
    assert not safety_approving("ABSTAIN insufficient evidence")
