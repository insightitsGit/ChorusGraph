"""Tests for production shadow replay."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from chorusgraph.shadow.replay.ingest import load_jsonl
from chorusgraph.shadow.replay.replay import run_temporal_replay, temporal_split
from chorusgraph.shadow.replay.report import build_slug_reports, format_production_report
from chorusgraph.shadow.replay.schema import TurnRecord
from chorusgraph.shadow.replay.stats import (
    MIN_HITS,
    Verdict,
    classify_verdict,
    clopper_pearson_upper,
    wilson_upper,
)
from chorusgraph.sections.models import CachePolicy


def _turn(i: int, query: str, response: str, slug: str = "site_kb") -> TurnRecord:
    base = datetime(2026, 6, 1, tzinfo=timezone.utc)
    return TurnRecord(
        query=query,
        category_slug=slug,
        response=response,
        timestamp=base + timedelta(hours=i),
        section_id=f"id-{i}",
    )


def test_temporal_split_70_30():
    records = [_turn(i, f"q{i}", f"a{i}") for i in range(10)]
    seed, eval_ = temporal_split(records, seed_fraction=0.70)
    assert len(seed) == 7
    assert len(eval_) == 3
    assert seed[-1].timestamp < eval_[0].timestamp


def test_load_jsonl(tmp_path: Path):
    p = tmp_path / "t.jsonl"
    row = {
        "query": "hello",
        "category_slug": "greeting",
        "response": "hi there",
        "timestamp": "2026-06-01T12:00:00+00:00",
        "section_id": "abc",
    }
    p.write_text(json.dumps(row) + "\n", encoding="utf-8")
    recs = load_jsonl(p)
    assert len(recs) == 1
    assert recs[0].category_slug == "greeting"


def test_classify_verdict_insufficient():
    assert classify_verdict(MIN_HITS - 1, 0.0) == Verdict.INSUFFICIENT_DATA


def test_classify_verdict_unsafe():
    assert classify_verdict(MIN_HITS, 0.05) == Verdict.UNSAFE


def test_classify_verdict_cacheable():
    assert classify_verdict(MIN_HITS, 0.005) == Verdict.CACHEABLE


def test_wilson_upper_zero_fp():
    upper = wilson_upper(0, 500)
    assert upper < 0.01


def test_clopper_pearson_upper_zero_fp():
    upper = clopper_pearson_upper(0, 500)
    assert upper < 0.01


def test_replay_on_synthetic_jsonl(tmp_path: Path):
    seed_q = "what is the hotel product price"
    seed_r = "Hotel agent is $5499"
    eval_q = "what is the hotel product price?"  # near paraphrase
    eval_r = "Hotel agent is $5499"
    rows = [
        {
            "query": seed_q,
            "category_slug": "site_kb",
            "response": seed_r,
            "timestamp": "2026-06-01T10:00:00+00:00",
            "section_id": "1",
        },
        {
            "query": eval_q,
            "category_slug": "site_kb",
            "response": eval_r,
            "timestamp": "2026-06-02T10:00:00+00:00",
            "section_id": "2",
        },
    ]
    p = tmp_path / "syn.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    result = run_temporal_replay(p, seed_fraction=0.5, verify_thresholds=(0.90,))
    assert result.seed_count == 1
    assert result.eval_count == 1
    reports = build_slug_reports(result)
    assert reports
    text = format_production_report(result, source="synthetic")
    assert "semantic coverage gap" in text.lower()


@pytest.mark.skipif(
    not (
        Path(__file__).resolve().parents[1]
        / "chorusgraph"
        / "shadow"
        / "replay"
        / "data"
        / "website_chat_turns.jsonl"
    ).exists(),
    reason="Production JSONL not downloaded",
)
def test_replay_on_production_export():
    jsonl = (
        Path(__file__).resolve().parents[1]
        / "chorusgraph"
        / "shadow"
        / "replay"
        / "data"
        / "website_chat_turns.jsonl"
    )
    records = load_jsonl(jsonl)
    assert len(records) >= 10
    result = run_temporal_replay(jsonl, verify_thresholds=(0.95,))
    report = format_production_report(result, source="website_chat_turns.jsonl")
    assert "INSUFFICIENT DATA" in report or "CACHEABLE" in report
    assert "semantic coverage gap" in report.lower()
