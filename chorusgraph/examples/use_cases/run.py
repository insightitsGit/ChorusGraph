"""LLM-free use-case demos for ChorusGraph stack patterns.

ReAct / Plan-Solve / Reflection / multi-agent / PrismCache / warm chunks / Cortex lifecycle.
No API key required for these stubs. Live Gemini: ``chorusgraph-finance-patterns``,
``chorusgraph-finance-memory``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from chorusgraph import SqliteLedgerSink, wrap
from chorusgraph.agents import Agent, PlanPolicy, PlanSolveOpts, ReActOpts, ReflectionOpts
from chorusgraph.agents.reflection import ValidationVerdict
from chorusgraph.cache_gate import gate, seed_cache_entry
from chorusgraph.compose import ChorusStack, KeywordRetrievalBackend
from chorusgraph.examples.multi_agent_graph import GRAPH_ID as MA_GRAPH_ID
from chorusgraph.examples.multi_agent_graph import TENANT_ID as MA_TENANT_ID
from chorusgraph.examples.multi_agent_graph import build_multi_agent_graph
from chorusgraph.examples.use_cases.cases import USE_CASES, by_pattern
from chorusgraph.memory.structured_recall import StructuredRecallContext
from chorusgraph.nodes.tool import ToolRegistry, ToolSpec
from chorusgraph.sections.models import CachePolicy, Section


def _fx_registry() -> ToolRegistry:
    """Deterministic FX tool (no Frankfurter / network)."""
    rates = {
        ("USD", "EUR"): 0.92,
        ("USD", "GBP"): 0.79,
    }

    def fetch_exchange_rate(from_currency: str, to_currency: str) -> Dict[str, Any]:
        key = (from_currency.upper(), to_currency.upper())
        if key not in rates:
            raise ValueError(f"unsupported pair {key[0]}/{key[1]}")
        return {
            "from_currency": key[0],
            "to_currency": key[1],
            "rate": rates[key],
            "source": "use_case_stub",
        }

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="fetch_exchange_rate",
            description="Fetch a stub FX rate (offline use-case demo)",
            fn=fetch_exchange_rate,
            parameters={
                "type": "object",
                "properties": {
                    "from_currency": {"type": "string"},
                    "to_currency": {"type": "string"},
                },
                "required": ["from_currency", "to_currency"],
            },
        )
    )
    return registry


def _stub_json_llm(responses: List[Dict[str, Any]]) -> Callable[[str, str], str]:
    call = {"n": 0}

    def llm_json(_system: str, _user: str) -> str:
        idx = min(call["n"], len(responses) - 1)
        call["n"] += 1
        return json.dumps(responses[idx])

    return llm_json


def _print_case_header(pattern: str) -> None:
    uc = by_pattern(pattern)
    print(f"\n{'=' * 64}")
    print(f"  Pattern: {uc.pattern}")
    print(f"  Use case: {uc.title}")
    print(f"  Domain: {uc.domain}")
    print(f"{'=' * 64}")
    print(f"Question: {uc.question}")
    print(f"Why: {uc.why}")
    print(f"Topology: {uc.topology}")
    print(f"When: {uc.when_to_use}")
    print(f"Stop: {uc.stop_condition}")


def run_react_use_case(registry: Optional[ToolRegistry] = None) -> Dict[str, Any]:
    uc = by_pattern("react")
    _print_case_header("react")
    registry = registry or _fx_registry()
    llm = _stub_json_llm(
        [
            {
                "thought": "Need USD/EUR first",
                "action": {
                    "tool": "fetch_exchange_rate",
                    "args": {"from_currency": "USD", "to_currency": "EUR"},
                },
                "finish": False,
            },
            {
                "thought": "Need USD/GBP next",
                "action": {
                    "tool": "fetch_exchange_rate",
                    "args": {"from_currency": "USD", "to_currency": "GBP"},
                },
                "finish": False,
            },
            {
                "thought": "EUR (0.92) needs more USD than GBP (0.79) → GBP stronger vs USD",
                "action": None,
                "finish": True,
                "finish_reason": "compared both pairs",
            },
        ]
    )
    agent = Agent(
        pattern="react",
        tools=registry,
        model=llm,
        policy=PlanPolicy(max_steps=6),
        pattern_opts=ReActOpts(max_tool_calls=4, require_tool_before_finish=True),
    )
    result = agent.run(uc.question)
    print(f"Finished: {result.finished} ({result.finish_reason})")
    print(f"Tool calls: {len(result.tool_calls)}")
    for tc in result.tool_calls:
        print(f"  - {tc.get('tool')} ok={tc.get('ok')} → {tc.get('data')}")
    print(f"Trace steps: {len(result.trace)}")
    for step in result.trace:
        kind = step.kind.value if hasattr(step.kind, "value") else step.kind
        print(f"  [{kind}] {(step.content or '')[:100]}")
    return {"use_case": uc, "result": result}


def run_plan_solve_use_case(registry: Optional[ToolRegistry] = None) -> Dict[str, Any]:
    uc = by_pattern("plan_solve")
    _print_case_header("plan_solve")
    registry = registry or _fx_registry()
    # Static plan: two tool fetches + a non-tool compute step (engine derives EUR/GBP).
    plan = {
        "steps": [
            {
                "id": 1,
                "description": "Fetch USD/EUR",
                "tool": "fetch_exchange_rate",
                "args": {"from_currency": "USD", "to_currency": "EUR"},
            },
            {
                "id": 2,
                "description": "Fetch USD/GBP",
                "tool": "fetch_exchange_rate",
                "args": {"from_currency": "USD", "to_currency": "GBP"},
            },
            {
                "id": 3,
                "description": "Compute EUR/GBP cross-rate from USD legs",
                "tool": "",
                "args": {},
            },
        ]
    }
    llm = _stub_json_llm([plan])
    agent = Agent(
        pattern="plan_solve",
        tools=registry,
        model=llm,
        policy=PlanPolicy(max_steps=8),
        pattern_opts=PlanSolveOpts(max_plan_steps=5, validate_plan=True),
    )
    result = agent.run(uc.question)
    print(f"Finished: {result.finished} ({result.finish_reason})")
    print(f"Plan length: {len(result.plan)}")
    print(f"Tool calls: {len(result.tool_calls)}")
    for tc in result.tool_calls:
        print(f"  - {tc.get('tool')} ok={tc.get('ok')} → {tc.get('data')}")
    for obs in result.observations:
        if isinstance(obs, dict) and obs.get("computed"):
            print(f"  - computed cross → {obs.get('data')}")
    return {"use_case": uc, "result": result}


def run_reflection_use_case() -> Dict[str, Any]:
    uc = by_pattern("reflection")
    _print_case_header("reflection")

    def validate(text: str) -> ValidationVerdict:
        if "0.9900" in text or "0.99" in text:
            return ValidationVerdict(approved=False, notes=["wrong USD/EUR figure"])
        if "0.92" in text and "0.79" in text:
            return ValidationVerdict(approved=True, notes=["figures match stub tools"])
        return ValidationVerdict(approved=False, notes=["missing required rates"])

    def revise(_text: str, _verdict: ValidationVerdict) -> str:
        return (
            "USD/EUR is 0.92 and USD/GBP is 0.79 (stub tools). "
            "GBP is stronger against USD (fewer GBP per USD)."
        )

    registry = _fx_registry()
    agent = Agent(
        pattern="reflection",
        tools=registry,
        model=lambda _s, _u: "{}",
        policy=PlanPolicy(max_steps=4, max_reflection_passes=2),
        pattern_opts=ReflectionOpts(max_revisions=2, stop_when_no_improvement=True),
    )
    result = agent.run(
        uc.question,
        initial_draft="USD/EUR is 0.9900 and USD/GBP is 0.79 (incorrect EUR).",
        validate=validate,
        revise=revise,
    )
    print(f"Finished: {result.finished} approved={result.approved}")
    print(f"Final draft: {result.draft}")
    print(f"Passes: {result.passes}")
    print(f"Trace steps: {len(result.trace)}")
    for step in result.trace:
        kind = step.kind.value if hasattr(step.kind, "value") else step.kind
        print(f"  [{kind}] {(step.content or '')[:120]}")
    return {"use_case": uc, "result": result}


def run_cache_use_case() -> Dict[str, Any]:
    """Built-in PrismCache via ChorusStack.defaults — miss, seed, hit (no API key)."""
    uc = by_pattern("cache")
    _print_case_header("cache")
    query = uc.question
    paraphrase = "USD/EUR rate please"
    fx_value = {
        "from_currency": "USD",
        "to_currency": "EUR",
        "rate": 0.92,
        "source": "use_case_stub",
    }

    stack = ChorusStack.defaults(tenant_id="use-case-cache-demo")
    cache = stack.resolve_cache()
    sidecar = stack.resolve_sidecar()
    section = Section(
        section_id="fx",
        category_slug="fx_rates",
        content=query,
        cache_policy=CachePolicy.REPLAY_SAFE,
    )

    miss = gate(query, section, cache, sidecar, coarse_threshold=0.88, verify_threshold=0.95)
    print(f"Turn 1 (cold): kind={miss.kind.value} is_hit={miss.is_hit}")
    print("  -> continue graph: tools / ReAct / writer, then seed cache")

    seed_cache_entry(
        cache,
        sidecar,
        query=query,
        value=fx_value,
        category_slug="fx_rates",
        cache_policy="replay_safe",
    )
    print(f"Seeded PrismCache for: {query!r}")

    hit = gate(query, section, cache, sidecar, coarse_threshold=0.88, verify_threshold=0.95)
    print(
        f"Turn 2 (repeat): kind={hit.kind.value} is_hit={hit.is_hit} "
        f"score={hit.verify_score or hit.coarse_score}"
    )
    print(f"  cached value: {hit.value}")
    print("  -> cache_gate routes straight to writer (skip LLM tools)")

    para_section = Section(
        section_id="fx",
        category_slug="fx_rates",
        content=paraphrase,
        cache_policy=CachePolicy.REPLAY_SAFE,
    )
    # Also seed the paraphrase phrase (finance agents do this after tool success).
    seed_cache_entry(
        cache,
        sidecar,
        query=paraphrase,
        value=fx_value,
        category_slug="fx_rates",
        cache_policy="replay_safe",
    )
    para = gate(
        paraphrase,
        para_section,
        cache,
        sidecar,
        coarse_threshold=0.88,
        verify_threshold=0.95,
    )
    print(f"Turn 3 (paraphrase seed): kind={para.kind.value} is_hit={para.is_hit}")
    print(f"Backend: {getattr(cache, 'name', type(cache).__name__)} (ChorusStack default)")

    return {
        "use_case": uc,
        "miss": miss,
        "hit": hit,
        "paraphrase": para,
        "backend": getattr(cache, "name", type(cache).__name__),
    }


def run_multi_agent_use_case() -> Dict[str, Any]:
    uc = by_pattern("multi_agent")
    _print_case_header("multi_agent")
    compiled = build_multi_agent_graph()
    wrapped = wrap(
        compiled,
        tenant_id=MA_TENANT_ID,
        graph_id=MA_GRAPH_ID,
        sink=SqliteLedgerSink(":memory:"),
    )
    result = wrapped.invoke({"message": uc.question})
    path = [s.node for s in wrapped.last_ledger.steps] if wrapped.last_ledger else []
    print(f"Response: {result.get('response', '')}")
    print(f"Validation: {result.get('validation')}")
    print(f"Ledger path: {' -> '.join(path)}")
    for step in wrapped.last_ledger.steps if wrapped.last_ledger else []:
        chain = getattr(step, "rule_chain", None) or []
        print(f"  [{step.node}] rule_chain={chain}")
    return {"use_case": uc, "result": result, "ledger_nodes": path}


def run_warm_chunks_use_case() -> Dict[str, Any]:
    """ADR-005 warm path using KeywordRetrievalBackend partitions (no chromadb required)."""
    uc = by_pattern("warm_chunks")
    _print_case_header("warm_chunks")

    backend = KeywordRetrievalBackend()
    backend.index(
        [
            {
                "id": "md1",
                "topic": "kb",
                "text": "PrismCache reduces LLM API costs with semantic recall across paraphrases",
                "source": "docs",
            },
            {
                "id": "md2",
                "topic": "kb",
                "text": "Warm chunk vectors avoid re-encoding the knowledge corpus every turn",
                "source": "docs",
            },
        ],
        partition="kb_markdown",
        version="docs-v1",
    )
    backend.index(
        [
            {
                "id": "cat1",
                "topic": "catalog",
                "text": "Hotel AI Web Agent 5499 one-time license",
                "source": "db",
            }
        ],
        partition="catalog",
        version="cat-v1",
    )

    stack = ChorusStack.defaults(tenant_id="use-case-warm", enable_memory=False).with_retrieval(backend)
    stack.warm_retrieval(partition="kb_markdown")
    stack.warm_retrieval(partition="catalog")

    assert stack.retrieval_ready(partition="kb_markdown")
    assert stack.retrieval_ready(partition="catalog")
    stats = stack.retrieval_stats()
    print(f"retrieval_ready kb_markdown={stack.retrieval_ready(partition='kb_markdown')}")
    print(f"partition_versions={dict(stats.partition_versions) if stats else {}}")

    kb_hits = backend.retrieve("kb", uc.question, top_k=1, partition="kb_markdown")
    cat_hits = backend.retrieve("catalog", "hotel agent", top_k=1, partition="catalog")
    print(f"kb hit: {kb_hits[0]['id']} - {kb_hits[0]['text'][:70]}...")
    print(f"catalog hit: {cat_hits[0]['id']} - {cat_hits[0]['text'][:70]}...")

    # Catalog update must NOT invalidate kb_markdown (partition isolation).
    backend.index(
        [
            {
                "id": "cat1",
                "topic": "catalog",
                "text": "Hotel AI Web Agent 5499 one-time license",
                "source": "db",
            },
            {
                "id": "cat2",
                "topic": "catalog",
                "text": "Updated catalog SKU 6100",
                "source": "db",
            },
        ],
        partition="catalog",
        version="cat-v2",
    )
    stats2 = stack.retrieval_stats()
    print(
        "Re-indexed catalog -> cat-v2; kb_markdown still "
        f"{(stats2.partition_versions if stats2 else {}).get('kb_markdown')}"
    )
    kb_after = backend.retrieve("kb", uc.question, top_k=1, partition="kb_markdown")
    print(f"kb still ready: id={kb_after[0]['id']} (partition isolation)")

    handler = stack.to_retrieve_handler(
        topic="kb",
        partition="kb_markdown",
        rerank_policy="vectors_only",
    )
    update = handler({"message": uc.question, "topic": "kb"})
    print(f"retrieve handler retrieved={len(update.get('retrieved') or [])}")
    print(f"rule_chain={update.get('rule_chain')}")
    print("PrismRAG tip: index(..., partition=, version=) stores vector_64; warm must not re-embed.")

    return {
        "use_case": uc,
        "kb_hits": kb_hits,
        "catalog_hits": cat_hits,
        "kb_after_catalog_bump": kb_after,
        "update": update,
        "ready": stack.retrieval_ready(partition="kb_markdown"),
        "versions": dict(stats2.partition_versions) if stats2 else {},
    }


@dataclass
class _TeachingCortex:
    """Demonstrates the MemoryBackend contract without Gemini.

    Live PrismCortex: ``chorusgraph-finance-memory`` / ``CortexMemoryBackend``.
    """

    name: str = "teaching_cortex"
    digests: List[Dict[str, str]] = field(default_factory=list)
    facts: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def schedule_digest(self, payload: str, *, source_id: str) -> None:
        # Off hot path — record only; real Cortex digests async via AsyncDigester.
        text = payload.strip()
        self.digests.append({"source_id": source_id, "payload": text})
        lower = text.lower()
        if "moderate risk" in lower or "risk tolerance" in lower:
            self.facts["risk_tolerance"] = {
                "fact": "User prefers moderate risk",
                "confidence": 0.91,
                "source_id": source_id,
            }
        if "usd" in lower and "eur" in lower and "prefer" in lower:
            self.facts["fx_preference"] = {
                "fact": "User prefers USD/EUR pairs",
                "confidence": 0.88,
                "source_id": source_id,
            }

    def recall_structured(
        self,
        query: str,
        *,
        cache: Any = None,
        raw_384: Any = None,
    ) -> Optional[StructuredRecallContext]:
        q = query.lower()
        evidence: List[Dict[str, Any]] = []
        if "risk" in q and "risk_tolerance" in self.facts:
            evidence.append(dict(self.facts["risk_tolerance"]))
        if ("eur" in q or "fx" in q or "prefer" in q) and "fx_preference" in self.facts:
            evidence.append(dict(self.facts["fx_preference"]))
        if not evidence:
            return None  # right: no demo fallback prose
        conf = min(e["confidence"] for e in evidence)
        return StructuredRecallContext(
            query_vector_64=[0.0] * 64,
            category_slug="user_profile",
            evidence=evidence,
            confidence=conf,
            freshness=datetime.now(timezone.utc),
            subgraph_hash="teaching-demo",
            cache_hit=False,
        )


def run_cortex_use_case() -> Dict[str, Any]:
    """Right PrismCortex lifecycle — LLM-free teaching stub + live CLI pointer."""
    uc = by_pattern("cortex")
    _print_case_header("cortex")

    print("WRONG:")
    print("  - Put user preferences in L1 whole-answer cache (wrong scope / risk)")
    print("  - Call digest() synchronously before returning the HTTP response")
    print("  - Re-inject the full chat transcript into every hop")
    print("RIGHT:")
    print("  - recall_structured at ingress -> memory_confidence / memory_evidence")
    print("  - Gate hops on confidence/freshness; empty recall = continue (no fake answer)")
    print("  - schedule_digest AFTER response (async, off the hot path)")

    memory = _TeachingCortex()
    # Simulate turn 1: answer then async digest (would be schedule_turn_digest in finance runtime).
    t0 = time.perf_counter()
    memory.schedule_digest(
        "User said: I prefer moderate risk for FX trades. Assistant confirmed.",
        source_id="turn-1",
    )
    digest_ms = (time.perf_counter() - t0) * 1000
    print(f"\nTurn 1 egress: schedule_digest returned in {digest_ms:.2f} ms (non-blocking stub)")

    # Turn 2: new session / thread — recall at ingress.
    query = uc.question
    recall = memory.recall_structured(query)
    assert recall is not None
    state = recall.to_memory_state()
    print(f"Turn 2 ingress recall: confidence={state['memory_confidence']}")
    print(f"  memory_recall: {state['memory_recall']}")
    print(f"  evidence: {state['memory_evidence']}")

    empty = memory.recall_structured("What is the weather in Dallas?")
    print(f"Unrelated query recall: {empty}  (no fabricated fallback)")

    print("\nWire with ChorusStack (live):")
    print("  stack = ChorusStack.defaults(tenant_id=...).  # memory=CortexMemoryBackend")
    print("  # or chorusgraph-finance-memory for thread resume + cross-session Cortex")

    return {
        "use_case": uc,
        "digest_ms": digest_ms,
        "recall_state": state,
        "empty_recall": empty,
        "digests": list(memory.digests),
        "backend": memory.name,
    }


def list_use_cases() -> None:
    print("ChorusGraph use cases (patterns, multi-agent, cache, warm chunks, Cortex)\n")
    for uc in USE_CASES:
        print(f"  [{uc.pattern}] {uc.title}")
        print(f"            {uc.when_to_use}")
        print()


def run_all() -> Dict[str, Any]:
    list_use_cases()
    out = {
        "react": run_react_use_case(),
        "plan_solve": run_plan_solve_use_case(),
        "reflection": run_reflection_use_case(),
        "multi_agent": run_multi_agent_use_case(),
        "cache": run_cache_use_case(),
        "warm_chunks": run_warm_chunks_use_case(),
        "cortex": run_cortex_use_case(),
    }
    print(f"\n{'=' * 64}")
    print("  Summary — full use-case suite completed (LLM-free)")
    print("  Live Gemini: chorusgraph-finance-patterns | chorusgraph-finance-memory")
    print("  Interactive walkthrough: website/demo.html")
    print(f"{'=' * 64}\n")
    return out


_RUNNERS = {
    "react": run_react_use_case,
    "plan_solve": run_plan_solve_use_case,
    "reflection": run_reflection_use_case,
    "multi_agent": run_multi_agent_use_case,
    "cache": run_cache_use_case,
    "warm_chunks": run_warm_chunks_use_case,
    "cortex": run_cortex_use_case,
}


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "ChorusGraph use-case demos: patterns, multi-agent, PrismCache, "
            "warm chunks, PrismCortex lifecycle (no API key for stubs)"
        ),
    )
    parser.add_argument(
        "pattern",
        nargs="?",
        choices=[*list(_RUNNERS), "all"],
        default="all",
        help="Which use case to run (default: all)",
    )
    parser.add_argument("--list", action="store_true", help="List use cases and exit")
    args = parser.parse_args(argv)

    try:
        if args.list:
            list_use_cases()
            return
        if args.pattern == "all":
            run_all()
        else:
            _RUNNERS[args.pattern]()
    except Exception as exc:  # noqa: BLE001 — CLI surface
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
