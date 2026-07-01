"""Production shadow replay — temporal split on real hub query logs."""

from chorusgraph.shadow.replay.ingest import load_jsonl
from chorusgraph.shadow.replay.replay import run_temporal_replay, temporal_split
from chorusgraph.shadow.replay.report import build_slug_reports, format_production_report, recommend_thresholds
from chorusgraph.shadow.replay.schema import TurnRecord
from chorusgraph.shadow.replay.stats import MIN_HITS, Verdict

__all__ = [
    "MIN_HITS",
    "TurnRecord",
    "Verdict",
    "build_slug_reports",
    "format_production_report",
    "load_jsonl",
    "recommend_thresholds",
    "run_temporal_replay",
    "temporal_split",
]
