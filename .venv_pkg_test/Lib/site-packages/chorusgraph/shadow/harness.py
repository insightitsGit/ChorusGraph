"""Shadow-mode harness — log gate decisions, never serve from cache."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from chorusgraph.cache_gate import gate, seed_cache_entry
from chorusgraph.cache_gate.decision import DecisionKind
from chorusgraph.cache_gate.sidecar import SidecarStore
from chorusgraph.ledger.instrument import make_cache_gate_step
from chorusgraph.ledger.models import RouteLedger
from chorusgraph.policy.embedder_guard import build_guarded_cache
from chorusgraph.sections.models import CachePolicy, Section
from chorusgraph.shadow.report import VERIFY_THRESHOLDS, format_report, frontier_table
from chorusgraph.shadow.results_store import ShadowResultsStore, ShadowRow

DEFAULT_DATASET = Path(__file__).parent / "dataset" / "labeled_queries.json"


@dataclass
class ShadowResult:
    ledger: RouteLedger
    report: str
    frontier: list
    rows: List[ShadowRow]


def _load_dataset(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _compare_values(expected: Any, actual: Any) -> bool:
    if expected == actual:
        return True
    if isinstance(expected, dict) and isinstance(actual, dict):
        return expected == actual
    return False


def _truth_for_case(case: dict, canonical_value: Any, equivalent: bool) -> Any:
    if equivalent:
        return canonical_value
    return case.get("truth", canonical_value)


def _verdict_for_decision(
    decision_kind: DecisionKind,
    *,
    equivalent: bool,
    would_value: Any,
    truth: Any,
    cache_policy: CachePolicy,
) -> str:
    if decision_kind == DecisionKind.MISS:
        return "miss_ok" if not equivalent else "miss_fn"
    if cache_policy == CachePolicy.SEMANTIC:
        return "semantic_ineligible"
    if decision_kind == DecisionKind.HIT_AS_CONTEXT:
        return "semantic_ineligible"
    if _compare_values(truth, would_value):
        return "match"
    return "mismatch"


def run_shadow_measurement(
    *,
    dataset_path: Path | None = None,
    tenant_id: str = "shadow-tenant",
    coarse_threshold: float = 0.88,
    verify_thresholds: tuple[float, ...] = VERIFY_THRESHOLDS,
    results_db: str | Path = ":memory:",
) -> ShadowResult:
    """
    Run shadow protocol §6: gate decides, logs only, never serves.

    Seeds one canonical entry per cluster, then evaluates all labeled cases
    across verify-threshold sweeps.
    """
    dataset = _load_dataset(dataset_path or DEFAULT_DATASET)
    cache = build_guarded_cache(tenant_id)
    sidecar = SidecarStore(":memory:")
    store = ShadowResultsStore(results_db)

    ledger = RouteLedger(tenant_id=tenant_id, graph_id="shadow-cache-gate")
    all_rows: list[ShadowRow] = []

    for cluster in dataset["clusters"]:
        slug = cluster["slug"]
        policy = CachePolicy(cluster["cache_policy"])
        canonical = cluster["canonical"]
        canonical_query = canonical["query"]
        canonical_value = canonical["value"]

        section_seed = Section(
            section_id=f"{slug}_canonical",
            category_slug=slug,
            content=canonical_value,
            cache_policy=policy,
        )
        seed_cache_entry(
            cache,
            sidecar,
            query=canonical_query,
            value=canonical_value,
            category_slug=slug,
            cache_policy=policy.value,
        )

        cases = list(cluster.get("cases", []))
        for case in cases:
            query = case["query"]
            equivalent = bool(case.get("equivalent", False))
            truth = _truth_for_case(case, canonical_value, equivalent)
            eval_section = Section(
                section_id=f"{slug}_eval",
                category_slug=slug,
                content=query,
                cache_policy=policy,
            )

            for verify_threshold in verify_thresholds:
                decision = gate(
                    query,
                    eval_section,
                    cache,
                    sidecar,
                    coarse_threshold=coarse_threshold,
                    verify_threshold=verify_threshold,
                )
                would_serve = decision.counts_for_fp
                would_value = decision.value if would_serve else None
                verdict = _verdict_for_decision(
                    decision.kind,
                    equivalent=equivalent,
                    would_value=would_value,
                    truth=truth,
                    cache_policy=policy,
                )

                row = ShadowRow(
                    query=query,
                    slug=slug,
                    cache_policy=policy.value,
                    coarse_score=decision.coarse_score,
                    verify_score=decision.verify_score,
                    verify_threshold=verify_threshold,
                    decision=decision.kind.value,
                    equivalent=equivalent,
                    verdict=verdict,
                    is_hit=decision.is_hit,
                    fp_eligible=decision.counts_for_fp,
                )
                store.insert(row)
                all_rows.append(row)

                if verify_threshold == verify_thresholds[len(verify_thresholds) // 2]:
                    ledger.add_step(
                        make_cache_gate_step(
                            node="cache_gate",
                            decision=decision,
                        )
                    )

    frontier = frontier_table(all_rows)
    report = format_report(frontier)
    return ShadowResult(ledger=ledger, report=report, frontier=frontier, rows=all_rows)


def main() -> None:
    result = run_shadow_measurement()
    print(result.report)
    print()
    print(f"Ledger steps with cache_hit populated: {sum(1 for s in result.ledger.steps if s.cache_hit is not None)}")
    print(f"Total shadow rows: {len(result.rows)}")


if __name__ == "__main__":
    main()
