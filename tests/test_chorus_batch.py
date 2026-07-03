"""T6 — ChorusBatchFrame property tests."""

from __future__ import annotations

from chorusgraph.transport.chorus import (
    ChorusBatchFrame,
    ChorusFrame,
    ChorusSpine,
    decode_batch_frame,
    encode_batch_frame,
)


def test_batch_frame_round_trip_bytes():
    frames = [
        ChorusFrame(
            envelope_id=f"e{i}",
            vector_64=[float(i) / 10.0] * 64,
            hop="worker",
            tenant_id="t",
            artifact_ref=f"ref-{i}",
        )
        for i in range(5)
    ]
    batch = encode_batch_frame(frames)
    assert batch.shape == (5, 64)
    raw = batch.to_bytes()
    restored = ChorusBatchFrame.from_bytes(raw, artifact_refs=batch.artifact_refs)
    assert restored.shape == (5, 64)
    decoded = decode_batch_frame(restored)
    assert len(decoded) == 5
    assert decoded[2].artifact_ref == "ref-2"


def test_spine_batch_encode_decode():
    spine = ChorusSpine(tenant_id="t")
    frames = [
        spine.encode_frame(
            envelope_id="a",
            vector_64=[0.5] * 64,
            hop="h",
            artifact_ref="art",
        )
    ]
    batch = encode_batch_frame(frames)
    assert batch.metadata["count"] == 1
