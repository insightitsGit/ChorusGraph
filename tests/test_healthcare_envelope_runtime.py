"""Tests for healthcare envelope runtime."""

from __future__ import annotations

import time

from benchmark.hc2.artifacts import compact_json
from benchmark.hc2.runtime import make_healthcare_envelope_runtime
from chorusgraph.transforms.projector import project_text


def test_envelope_uses_compact_json_not_python_repr():
    runtime = make_healthcare_envelope_runtime(tenant_id="compact-json-test")
    artifact = {"facts": "brief", "drugs": ["warfarin"], "topic": "anticoagulation"}
    compact = compact_json(artifact)
    repr_text = str(artifact)
    assert compact != repr_text
    assert "'" not in compact or '"' in compact

    _, env_compact = project_text(runtime.cache, compact)
    _, env_repr = project_text(runtime.cache, repr_text)
    assert list(env_compact.vector) != list(env_repr.vector)


def test_compact_artifact_shrinks_intake():
    from benchmark.hc2.artifacts import compact_artifact

    big = {"facts": "x" * 500, "drugs": ["a"] * 10, "question": "q" * 200}
    slim = compact_artifact("intake", big)
    assert len(slim.get("facts", "")) <= 200
    assert len(slim.get("drugs") or []) <= 8


def test_healthcare_runtime_skips_cortex():
    started = time.perf_counter()
    runtime = make_healthcare_envelope_runtime(tenant_id="no-cortex-test")
    elapsed_ms = (time.perf_counter() - started) * 1000
    assert runtime.cortex is None
    assert runtime.cache is not None
    assert elapsed_ms < 200
