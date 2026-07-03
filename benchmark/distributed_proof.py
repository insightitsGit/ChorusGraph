#!/usr/bin/env python3
"""T8 — Measured distributed transport proof (LOOPBACK tier, environment disclosed)."""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chorusgraph.core.constants import END, START
from chorusgraph.core.graph import Graph
from chorusgraph.core.node import NodeContext, dict_node_adapter, native_node
from chorusgraph.core.send import Send
from chorusgraph.core.subgraph import SubgraphSpec
from chorusgraph.core.subgraph_transport import invoke_remote_send_batch
from chorusgraph.core.transport_router import TransportRouter
from chorusgraph.transport.chorus import ChorusSpine
from chorusgraph.transport.modes import TransportMode


@dataclass
class ProofRow:
    config: str
    wall_ms: float
    wire_bytes: int
    batch_round_trips: int
    remote_embed_calls: int


class _StubLLM:
    """Deterministic stub — transport-only variance."""

    calls = 0

    def invoke(self, _prompt: str) -> str:
        _StubLLM.calls += 1
        return "stub"


@native_node
def map_stub(ctx: NodeContext):
    items = ctx.read().get("items") or [str(i) for i in range(10)]
    return [Send("remote", {"item": x}) for x in items]


@native_node
def reduce_stub(ctx: NodeContext):
    outputs = ctx.read().get("branch_outputs") or []
    return ctx.publish(artifact={"count": len(outputs)})


def _child_graph():
    @native_node
    def worker(ctx: NodeContext):
        return ctx.publish(artifact={"item": ctx.read().get("item"), "processed": True})

    g = Graph()
    g.add_node("worker", worker)
    g.add_edge(START, "worker")
    g.add_edge("worker", END)
    return g.compile()


def _remote_executor(batch: Any, spec: SubgraphSpec, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    from chorusgraph.core.subgraph_transport import decode_boundary_envelope

    out: List[Dict[str, Any]] = []
    for idx, ref in enumerate(batch.artifact_refs):
        import json as _json

        payload = _json.loads(ref) if str(ref).startswith("{") else {"item": ref}
        child_input = decode_boundary_envelope(
            {"vector_64": batch.vectors[idx], "artifact_ref": ref, "envelope_id": f"p-{idx}"}
        )
        child_input.update(payload)
        values = spec.child.invoke(child_input, config=config)
        out.append({"item": values.get("item"), "processed": True})
    return out


def _run_config(label: str, *, mode: TransportMode, prismapi: bool = False) -> ProofRow:
    from chorusgraph.core.send import BranchTask, branch_id_for

    child = _child_graph()
    spec = SubgraphSpec(
        name="remote",
        child=child,
        input_map={"item": "item"},
        output_map={"processed": "processed", "item": "item"},
        location="prismapi" if prismapi else "chorus",
    )
    tasks = [
        BranchTask(branch_id=branch_id_for("map", 1, i), target="remote", payload={"item": str(i)})
        for i in range(10)
    ]
    router = TransportRouter(
        tenant_id="proof",
        mode=mode,
        chorus=ChorusSpine(tenant_id="proof") if mode != TransportMode.INPROC else None,
        remote_batch_handler=_remote_executor,
    )
    remote_embeds = 0
    if prismapi:
        from chorusgraph.transport.prismapi import PrismAPISpine

        spine = PrismAPISpine(tenant_id="proof")
        router.prismapi_client = spine
        remote_embeds = spine.remote_embed_calls

    t0 = time.perf_counter()
    invoke_remote_send_batch(
        spec,
        tasks,
        config={"configurable": {"thread_id": f"proof-{label}", "tenant_id": "proof"}},
        transport=router,
        remote_executor=_remote_executor,
    )
    wall_ms = (time.perf_counter() - t0) * 1000.0
    return ProofRow(
        config=label,
        wall_ms=wall_ms,
        wire_bytes=router.wire_bytes,
        batch_round_trips=router.batch_deliveries,
        remote_embed_calls=remote_embeds,
    )


def run_proof(*, out_dir: Path) -> Dict[str, Any]:
    env = {
        "tier": "LOOPBACK",
        "host": platform.node(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "processes": 2,
        "note": "Local loopback — not multi-VM Azure",
    }
    rows = [
        _run_config("inproc", mode=TransportMode.INPROC),
        _run_config("chorus_loopback", mode=TransportMode.CHORUS_LOCAL),
        _run_config("prismapi_loopback", mode=TransportMode.CHORUS_FEDERATED, prismapi=True),
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"environment": env, "rows": [asdict(r) for r in rows]}
    path = out_dir / "distributed_proof.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md = out_dir / "DISTRIBUTED_PROOF.md"
    md.write_text(
        "\n".join(
            [
                "# Distributed transport proof (LOOPBACK)",
                "",
                f"- Host: `{env['host']}`",
                f"- Python: `{env['python']}`",
                f"- UTC: `{env['timestamp_utc']}`",
                "",
                "| Config | wall_ms | wire_bytes | batch_RTs | remote_embeds |",
                "|--------|---------|------------|-----------|---------------|",
                *[
                    f"| {r.config} | {r.wall_ms:.2f} | {r.wire_bytes} | {r.batch_round_trips} | {r.remote_embed_calls} |"
                    for r in rows
                ],
            ]
        ),
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run distributed transport proof (T8)")
    parser.add_argument(
        "--out",
        default=str(ROOT / "benchmark" / "results" / "distributed_proof"),
        help="Output directory",
    )
    args = parser.parse_args()
    payload = run_proof(out_dir=Path(args.out))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
