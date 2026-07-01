"""Shadow-mode measurement for cache gate false-positive rate."""

from chorusgraph.shadow.report import VERIFY_THRESHOLDS, format_report, frontier_table
from chorusgraph.shadow.results_store import ShadowResultsStore


def run_shadow_measurement(*args, **kwargs):
    from chorusgraph.shadow.harness import run_shadow_measurement as _run

    return _run(*args, **kwargs)


__all__ = [
    "ShadowResultsStore",
    "VERIFY_THRESHOLDS",
    "format_report",
    "frontier_table",
    "run_shadow_measurement",
]
