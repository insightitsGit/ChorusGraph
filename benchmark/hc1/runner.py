"""HC1 — ChorusGraph single-agent healthcare (core engine + cache + Route Ledger)."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Tuple

from benchmark.healthcare.abstain import should_abstain
from benchmark.healthcare.cache_gate import gate_healthcare_case
from benchmark.healthcare.retrieval import vector_retrieve_fn
from benchmark.healthcare.tools import check_drug_interactions
from benchmark.healthcare_workload import HealthcareCase
from benchmark.multiagent_measure import MultiAgentMeasurement, score_healthcare_answer
from benchmark.hc1.cache_helpers import (
    CLINICAL_SLUG,
    apply_cache_payload,
    build_hc1_cache_payload,
    cache_query_key,
    cache_seed_phrases,
)
from benchmark.hc1.runtime import GRAPH_ID, HC1_TENANT_ID, make_healthcare_hc1_runtime
from benchmark.hc2.cache_helpers import cache_fingerprint_key, seed_healthcare_cache
from benchmark.shared.healthcare_react import HEALTHCARE_REACT_SYSTEM, HEALTHCARE_WRITER_SYSTEM
from benchmark.shared.instrumented_gemini import InstrumentedGeminiClient
from benchmark.thresholds import measured_thresholds
from chorusgraph import SqliteLedgerSink, wrap
from chorusgraph.agents.react_utils import parse_react_json
from chorusgraph.core import END, Graph, START
from chorusgraph.core.node import NodeContext
from chorusgraph.core.channels import NodeUpdate
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime

MAX_REACT_STEPS = 6


def _read_view(ctx: NodeContext) -> Dict[str, Any]:
    """Normalize scalar types — checkpoints and JSON may store numbers as strings."""
    view = ctx.read()
    view["react_step"] = int(view.get("react_step") or 0)
    view["tool_calls"] = int(view.get("tool_calls") or 0)
    view["react_done"] = bool(view.get("react_done"))
    view["cache_hit"] = bool(view.get("cache_hit"))
    view["abstained"] = bool(view.get("abstained"))
    return view


def build_healthcare_graph_hc1(
    *,
    runtime: Optional[FinanceRuntime] = None,
    gemini: Optional[InstrumentedGeminiClient] = None,
    coarse_threshold: Optional[float] = None,
    verify_threshold: Optional[float] = None,
):
    thresholds = measured_thresholds()
    coarse_threshold = coarse_threshold if coarse_threshold is not None else thresholds.coarse
    verify_threshold = verify_threshold if verify_threshold is not None else thresholds.verify_for(CLINICAL_SLUG)
    gemini = gemini or InstrumentedGeminiClient()
    runtime = runtime or make_healthcare_hc1_runtime(gemini=gemini)

    def cache_gate(ctx: NodeContext) -> NodeUpdate:
        view = _read_view(ctx)
        case: HealthcareCase = view["case"]
        decision = gate_healthcare_case(
            runtime,
            case,
            coarse_threshold=coarse_threshold,
            verify_threshold=verify_threshold,
        )
        artifact: Dict[str, Any] = {
            "cache_hit": decision.is_hit,
            "cache_score": decision.verify_score or decision.coarse_score,
            "cache_coarse_score": decision.coarse_score,
            "cache_verify_score": decision.verify_score,
            "cache_decision": decision.kind.value if decision.kind else "miss",
        }
        if decision.is_hit and decision.value:
            artifact = apply_cache_payload(artifact, decision.value)
        return ctx.publish(artifact=artifact, category_slug=CLINICAL_SLUG, rule_chain=["cache_gate"])

    def react(ctx: NodeContext) -> NodeUpdate:
        view = _read_view(ctx)
        step = view["react_step"]
        if step >= MAX_REACT_STEPS:
            return ctx.publish(artifact={"react_done": True, "raw_output": "max_steps"}, category_slug="general")
        case: HealthcareCase = view["case"]
        user = (
            f"Clinical case:\n{case.presentation}\n"
            f"Topic: {case.topic}\nDrugs: {case.drugs}\n\n"
            f"Scratchpad:\n{view.get('scratchpad') or '(empty)'}"
        )
        raw = gemini.generate_json(HEALTHCARE_REACT_SYSTEM, user)
        parsed = parse_react_json(raw)
        action = parsed.get("action")
        finish = bool(parsed.get("finish"))
        has_action = bool(action and (action.get("tool") or action.get("name")))
        react_done = finish and not has_action
        if finish and has_action and step + 1 < MAX_REACT_STEPS:
            react_done = False
        elif finish:
            react_done = True
        return ctx.publish(
            artifact={
                "react_step": step + 1,
                "pending_action": action if has_action else None,
                "react_done": react_done,
                "raw_output": str(parsed.get("thought") or ""),
            },
            category_slug="general",
            rule_chain=[f"react/step={step + 1}"],
        )

    def tool(ctx: NodeContext) -> NodeUpdate:
        view = _read_view(ctx)
        case: HealthcareCase = view["case"]
        action = view.get("pending_action") or {}
        tool_name = action.get("tool") or action.get("name") or "retrieve_guidelines"
        args = dict(action.get("args") or action.get("arguments") or {})
        artifact: Dict[str, Any] = {
            "pending_action": None,
            "react_done": False,
            "tool_calls": view["tool_calls"] + 1,
        }
        if tool_name == "check_drug_interactions":
            drugs = args.get("drugs") or case.drugs
            result = check_drug_interactions(list(drugs))
            artifact["interactions"] = list(view.get("interactions") or []) + list(result)
            obs = json.dumps(result)
        else:
            topic = args.get("topic") or case.topic
            query = args.get("query") or case.presentation
            result = vector_retrieve_fn(str(topic), str(query))
            artifact["retrieved"] = list(view.get("retrieved") or []) + list(result)
            obs = json.dumps(result)
        scratch = (view.get("scratchpad") or "") + f"\nAction: {tool_name}\nObservation: {obs}\n"
        artifact["scratchpad"] = scratch
        artifact["raw_output"] = obs[:200]
        return ctx.publish(artifact=artifact, category_slug="general", rule_chain=[f"tool/{tool_name}"])

    def writer(ctx: NodeContext) -> NodeUpdate:
        view = _read_view(ctx)
        case: HealthcareCase = view["case"]
        retrieved = view.get("retrieved") or []
        interactions = view.get("interactions") or []
        cited = [str(d.get("id") or "") for d in retrieved if d.get("id")]
        safety = {"verdict": "APPROVED" if cited or interactions else "ABSTAIN"}
        abstained = should_abstain(
            case_topic=case.topic,
            retrieve_artifact={"cited_ids": cited},
            retrieved_docs=retrieved,
            safety_verdict=safety,
        )
        fp_state = {
            "case": case,
            "retrieved": retrieved,
            "interactions": interactions,
            "hop_artifacts": {
                "intake": {"drugs": case.drugs, "topic": case.topic, "facts": case.presentation},
                "retrieve": {"cited_ids": cited},
                "drug_check": {"interactions": interactions},
            },
        }
        if abstained or case.expected_abstain:
            response = (
                "I must abstain from a definitive clinical recommendation because "
                "grounded guideline or interaction evidence is insufficient for this case."
            )
            if runtime.cache is not None:
                seed_healthcare_cache(
                    runtime,
                    cache_query_key(case),
                    build_hc1_cache_payload({**view, "abstained": True}, response=response),
                    extra_queries=cache_seed_phrases(case),
                    pipeline_depth=case.pipeline_depth,
                    session_id=case.session_id,
                    fingerprint_key=cache_fingerprint_key(fp_state, case),
                    case=case,
                )
            return ctx.publish(
                artifact={"response": response, "abstained": True, "raw_output": response},
                category_slug="general",
            )
        user = (
            f"Case: {case.presentation}\n"
            f"Guidelines: {retrieved}\nInteractions: {interactions}\n"
            "Write a concise clinical recommendation citing sources."
        )
        response = gemini.generate(HEALTHCARE_WRITER_SYSTEM, user)
        if runtime.cache is not None:
            seed_healthcare_cache(
                runtime,
                cache_query_key(case),
                build_hc1_cache_payload({**view, "abstained": False}, response=response),
                extra_queries=cache_seed_phrases(case),
                pipeline_depth=case.pipeline_depth,
                session_id=case.session_id,
                fingerprint_key=cache_fingerprint_key(fp_state, case),
                case=case,
            )
        return ctx.publish(
            artifact={"response": response, "abstained": False, "raw_output": response},
            category_slug="general",
            rule_chain=["writer=gemini"],
        )

    def route_cache(view: dict) -> str:
        if view.get("cache_hit") and (view.get("retrieved") or view.get("interactions")):
            return "writer"
        return "react"

    def route_react(view: dict) -> str:
        if view.get("pending_action"):
            return "tool"
        if view.get("react_done") or int(view.get("react_step") or 0) >= MAX_REACT_STEPS:
            return "writer"
        return "react"

    def route_tool(view: dict) -> str:
        if int(view.get("react_step") or 0) >= MAX_REACT_STEPS:
            return "writer"
        return "react"

    g = Graph(tenant_id=HC1_TENANT_ID, graph_id=GRAPH_ID)
    g.add_node("cache_gate", cache_gate, category_slug=CLINICAL_SLUG)
    g.add_node("react", react)
    g.add_node("tool", tool)
    g.add_node("writer", writer)
    g.add_edge(START, "cache_gate")
    g.add_conditional_edges("cache_gate", route_cache, {"writer": "writer", "react": "react"})
    g.add_conditional_edges("react", route_react, {"tool": "tool", "writer": "writer", "react": "react"})
    g.add_conditional_edges("tool", route_tool, {"react": "react", "writer": "writer"})
    g.add_edge("writer", END)
    return g.compile(), gemini, runtime


class HC1Runner:
    """ChorusGraph core engine — shared global cache + Route Ledger (H21 T5)."""

    _shared_runtime: FinanceRuntime | None = None

    def __init__(self) -> None:
        self._thresholds = measured_thresholds()
        self._sink = SqliteLedgerSink(":memory:")
        self.last_ledger = None
        if HC1Runner._shared_runtime is None:
            HC1Runner._shared_runtime = make_healthcare_hc1_runtime()
        self._runtime = HC1Runner._shared_runtime
        self._gemini = InstrumentedGeminiClient()
        compiled, _, _ = build_healthcare_graph_hc1(
            runtime=self._runtime,
            gemini=self._gemini,
            coarse_threshold=self._thresholds.coarse,
            verify_threshold=self._thresholds.verify_for(CLINICAL_SLUG),
        )
        self.wrapped = wrap(
            compiled,
            tenant_id=HC1_TENANT_ID,
            graph_id=GRAPH_ID,
            sink=self._sink,
        )

    def run(self, case: HealthcareCase) -> MultiAgentMeasurement:
        gemini = self._gemini
        gemini.reset_usage()
        started = time.perf_counter()
        try:
            result = self.wrapped.invoke(
                {
                    "case": case,
                    "react_step": 0,
                    "scratchpad": "",
                    "react_done": False,
                    "pending_action": None,
                    "tool_calls": 0,
                    "retrieved": [],
                    "interactions": [],
                    "response": "",
                    "abstained": False,
                    "cache_hit": False,
                }
            )
            latency = int((time.perf_counter() - started) * 1000)
            self.last_ledger = self.wrapped.last_ledger
            answer = result.get("response") or ""
            abstained = bool(result.get("abstained"))
            return MultiAgentMeasurement(
                case_id=case.case_id,
                container="HC1",
                pipeline_depth=case.pipeline_depth,
                message=case.presentation,
                latency_ms=latency,
                llm_calls=gemini.usage.llm_calls,
                tokens_in=gemini.usage.tokens_in,
                tokens_out=gemini.usage.tokens_out,
                cost_usd=gemini.usage.cost_usd,
                task_success=score_healthcare_answer(
                    answer=answer,
                    must_cite=case.must_cite,
                    expected_abstain=case.expected_abstain,
                    abstained=abstained,
                ),
                abstained=abstained,
                answer=answer[:2000],
                tool_calls=int(result.get("tool_calls") or 0),
                variant=case.variant,
                cache_hit=bool(result.get("cache_hit")),
                cache_score=result.get("cache_score"),
            )
        except Exception as exc:
            latency = int((time.perf_counter() - started) * 1000)
            return MultiAgentMeasurement(
                case_id=case.case_id,
                container="HC1",
                pipeline_depth=case.pipeline_depth,
                message=case.presentation,
                latency_ms=latency,
                llm_calls=gemini.usage.llm_calls,
                tokens_in=gemini.usage.tokens_in,
                tokens_out=gemini.usage.tokens_out,
                cost_usd=gemini.usage.cost_usd,
                task_success=False,
                abstained=False,
                answer="",
                error=str(exc),
                variant=case.variant,
            )


__all__ = ["HC1Runner", "build_healthcare_graph_hc1"]
