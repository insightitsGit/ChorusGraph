"""Live pilot audit from Route Ledger — measured cache hits and latency."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean
from typing import Any, Dict, List, Optional

from chorusgraph.ledger.models import LedgerStep, RouteLedger
from chorusgraph.ledger.query import get_run, list_runs
from chorusgraph.ledger.sink import LedgerSink

LEDGER_DISCLAIMER = (
    "Measured from your production Route Ledger — actual cache hits and hop latency, "
    "not a text-similarity estimate. Modeled dollar savings are not available until "
    "LedgerStep records tokens_in/tokens_out (schema change pending Director sign-off)."
)

SCHEMA_GAP_NOTE = (
    "LedgerStep has cache_hit, cache_score, and duration_ms today but no token or cost "
    "fields. Live dollar reporting requires optional tokens_in/tokens_out on LedgerStep."
)


@dataclass
class LedgerAuditResult:
    run_id: str
    tenant_id: str
    graph_id: str
    created_at: datetime
    total_steps: int
    gate_steps: int
    measured_cache_hits: int
    measured_cache_misses: int
    measured_cache_hit_rate: float
    mean_duration_ms_hit: Optional[float] = None
    mean_duration_ms_miss: Optional[float] = None
    mean_cache_score_on_hits: Optional[float] = None
    latency_savings_ms_per_gate: Optional[float] = None
    node_duration_ms: Dict[str, float] = field(default_factory=dict)
    steps: List[LedgerStep] = field(default_factory=list)

    @property
    def has_cost_data(self) -> bool:
        return False


def _is_gate_step(step: LedgerStep) -> bool:
    name = (step.node or "").lower()
    return "cache" in name and "gate" in name


def _gate_steps(steps: List[LedgerStep]) -> List[LedgerStep]:
    gated = [s for s in steps if s.cache_hit is not None or _is_gate_step(s)]
    if gated:
        return gated
    return [s for s in steps if s.cache_hit is not None]


def analyze_ledger_run(ledger: RouteLedger) -> LedgerAuditResult:
    steps = list(ledger.steps)
    gates = _gate_steps(steps)
    hits = [s for s in gates if s.cache_hit is True]
    misses = [s for s in gates if s.cache_hit is False]
    gate_n = len(hits) + len(misses)

    hit_durations = [float(s.duration_ms) for s in hits if s.duration_ms]
    miss_durations = [float(s.duration_ms) for s in misses if s.duration_ms]
    scores = [float(s.cache_score) for s in hits if s.cache_score is not None]

    mean_hit = mean(hit_durations) if hit_durations else None
    mean_miss = mean(miss_durations) if miss_durations else None
    latency_savings = None
    if mean_hit is not None and mean_miss is not None:
        latency_savings = mean_miss - mean_hit

    by_node: dict[str, list[float]] = {}
    for s in steps:
        if s.duration_ms:
            by_node.setdefault(s.node, []).append(float(s.duration_ms))

    return LedgerAuditResult(
        run_id=ledger.run_id,
        tenant_id=ledger.tenant_id,
        graph_id=ledger.graph_id,
        created_at=ledger.created_at,
        total_steps=len(steps),
        gate_steps=gate_n,
        measured_cache_hits=len(hits),
        measured_cache_misses=len(misses),
        measured_cache_hit_rate=(len(hits) / gate_n) if gate_n else 0.0,
        mean_duration_ms_hit=mean_hit,
        mean_duration_ms_miss=mean_miss,
        mean_cache_score_on_hits=mean(scores) if scores else None,
        latency_savings_ms_per_gate=latency_savings,
        node_duration_ms={k: mean(v) for k, v in by_node.items()},
        steps=steps,
    )


def load_ledger_audit(
    sink: LedgerSink,
    run_id: str,
) -> Optional[LedgerAuditResult]:
    ledger = get_run(sink, run_id)
    if ledger is None:
        return None
    return analyze_ledger_run(ledger)


def ledger_audit_to_dict(result: LedgerAuditResult) -> Dict[str, Any]:
    return {
        "run_id": result.run_id,
        "tenant_id": result.tenant_id,
        "graph_id": result.graph_id,
        "created_at": result.created_at.isoformat(),
        "total_steps": result.total_steps,
        "gate_steps": result.gate_steps,
        "measured_cache_hits": result.measured_cache_hits,
        "measured_cache_misses": result.measured_cache_misses,
        "measured_cache_hit_rate": round(result.measured_cache_hit_rate, 4),
        "mean_duration_ms_on_cache_hit": result.mean_duration_ms_hit,
        "mean_duration_ms_on_cache_miss": result.mean_duration_ms_miss,
        "mean_cache_score_on_hits": result.mean_cache_score_on_hits,
        "estimated_latency_savings_ms_per_gate": result.latency_savings_ms_per_gate,
        "mean_duration_ms_by_node": {
            k: round(v, 2) for k, v in sorted(result.node_duration_ms.items())
        },
        "cost_estimate_available": False,
        "schema_gap": SCHEMA_GAP_NOTE,
        "disclaimer": LEDGER_DISCLAIMER,
        "custom_steps": [
            {
                "node": s.node,
                "kind": s.kind,
                "detail": s.detail,
                "duration_ms": s.duration_ms,
            }
            for s in result.steps
            if s.kind
        ],
    }


def format_ledger_console_report(result: LedgerAuditResult) -> str:
    lines = [
        "ChorusGraph Pilot Ledger Audit (measured production traffic)",
        "=" * 56,
        f"Run ID: {result.run_id}",
        f"Graph: {result.graph_id}  Tenant: {result.tenant_id}",
        f"Recorded: {result.created_at.isoformat()}",
        f"Total steps: {result.total_steps}",
        "",
        f"Measured cache hit rate: {result.measured_cache_hit_rate * 100:.1f}% "
        f"({result.measured_cache_hits}/{result.gate_steps} gate evaluations)",
    ]
    if result.mean_cache_score_on_hits is not None:
        lines.append(f"Mean cache score on hits: {result.mean_cache_score_on_hits:.3f}")
    if result.mean_duration_ms_hit is not None:
        lines.append(f"Mean gate duration (hit): {result.mean_duration_ms_hit:.1f} ms")
    if result.mean_duration_ms_miss is not None:
        lines.append(f"Mean gate duration (miss): {result.mean_duration_ms_miss:.1f} ms")
    if result.latency_savings_ms_per_gate is not None:
        lines.append(
            f"Estimated latency savings per gate hit: {result.latency_savings_ms_per_gate:.1f} ms "
            "(miss mean - hit mean; measured)"
        )
    if result.node_duration_ms:
        lines.append("")
        lines.append("Mean duration by node (measured):")
        for node, ms in sorted(result.node_duration_ms.items(), key=lambda x: -x[1]):
            lines.append(f"  {node}: {ms:.1f} ms")
    custom = [s for s in result.steps if s.kind]
    if custom:
        lines.append("")
        lines.append("Custom ledger steps (kind/detail):")
        for s in custom:
            detail = s.detail or {}
            lines.append(f"  {s.node}: kind={s.kind} detail={detail}")
    lines.append("")
    lines.append(f"Cost estimate: not available — {SCHEMA_GAP_NOTE}")
    lines.append("")
    lines.append(LEDGER_DISCLAIMER)
    return "\n".join(lines)


def format_ledger_markdown_report(result: LedgerAuditResult) -> str:
    lines = [
        "# ChorusGraph Pilot Ledger Audit",
        "",
        "_Measured from Route Ledger — not a cold-log simulation._",
        "",
        f"- **Run ID:** `{result.run_id}`",
        f"- **Graph:** `{result.graph_id}`",
        f"- **Tenant:** `{result.tenant_id}`",
        f"- **Recorded:** {result.created_at.isoformat()}",
        f"- **Measured cache hit rate:** {result.measured_cache_hit_rate * 100:.1f}% "
        f"({result.measured_cache_hits}/{result.gate_steps})",
    ]
    if result.latency_savings_ms_per_gate is not None:
        lines.append(
            f"- **Latency savings per gate hit (estimated):** "
            f"{result.latency_savings_ms_per_gate:.1f} ms"
        )
    lines.append("")
    lines.append("## Cost")
    lines.append("")
    lines.append(f"_{SCHEMA_GAP_NOTE}_")
    lines.append("")
    lines.append(f"_{LEDGER_DISCLAIMER}_")
    return "\n".join(lines)


def format_ledger_json_report(result: LedgerAuditResult) -> str:
    import json

    return json.dumps(ledger_audit_to_dict(result), indent=2)


def summarize_runs(sink: LedgerSink, *, limit: int = 20) -> List[Dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ledger in list_runs(sink, limit=limit):
        audit = analyze_ledger_run(ledger)
        rows.append(
            {
                "run_id": ledger.run_id,
                "graph_id": ledger.graph_id,
                "tenant_id": ledger.tenant_id,
                "created_at": ledger.created_at.isoformat(),
                "gate_steps": audit.gate_steps,
                "cache_hit_rate": round(audit.measured_cache_hit_rate, 4),
            }
        )
    return rows


__all__ = [
    "LEDGER_DISCLAIMER",
    "SCHEMA_GAP_NOTE",
    "LedgerAuditResult",
    "analyze_ledger_run",
    "format_ledger_console_report",
    "format_ledger_json_report",
    "format_ledger_markdown_report",
    "ledger_audit_to_dict",
    "load_ledger_audit",
    "summarize_runs",
]
