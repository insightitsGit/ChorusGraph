"""HC2 role-typed nodes — envelope handoffs, cache-aware (mirror FC2)."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from benchmark.hl2.runner import _record_hop
from benchmark.hc2.artifacts import (
    analyze_handoff_plain,
    bounded_docs,
    compact_json,
    drug_handoff_plain,
    parse_json_object,
    retrieve_handoff_plain,
    safety_handoff_plain,
    should_abstain,
    store_envelope_artifact,
    writer_handoff_plain,
)
from benchmark.hc2.cache_helpers import (
    build_cache_payload,
    cache_fingerprint_key,
    cache_query_key,
    cache_seed_phrases,
    first_judgment_hop_after_cache,
    gate_clinical,
    seed_healthcare_cache,
)
from benchmark.healthcare.prompts import (
    WRITER_MID_SYSTEM as HL2_WRITER_MID_SYSTEM,
    WRITER_SHALLOW_SYSTEM as HL2_WRITER_SHALLOW_SYSTEM,
    WRITER_SYSTEM as HL2_WRITER_SYSTEM,
)
from benchmark.hc2.prompts import (
    ANALYZE_D_SYSTEM,
    DRUG_D_SYSTEM,
    INTAKE_D_SYSTEM,
    RETRIEVE_D_SYSTEM,
    SAFETY_D_SYSTEM,
    WRITER_D_SYSTEM,
    WRITER_MID_D_SYSTEM,
    WRITER_SHALLOW_D_SYSTEM,
)
from benchmark.hc2.state import HealthcareVectorState
from benchmark.hc2.trace import trace_event
from benchmark.healthcare.prismrag_mapping import assign_clinical_category
from benchmark.healthcare.retrieval import make_healthcare_retrieve_handler
from benchmark.healthcare.tools import check_drug_interactions
from benchmark.shared.instrumented_gemini import InstrumentedGeminiClient
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime
from chorusgraph.transforms.projector import project_from_raw, project_text, raw_from_state


def _trace_ids(state: HealthcareVectorState) -> tuple[str, str]:
    case = state.get("case")
    if case is not None:
        return str(getattr(case, "case_id", "") or ""), str(getattr(case, "session_id", "") or "")
    return "", ""


def _hop_trace(
    state: HealthcareVectorState,
    hop: str,
    started: float,
    gemini: InstrumentedGeminiClient,
    **extra: Any,
) -> None:
    case_id, session_id = _trace_ids(state)
    trace_event(
        "hop_end",
        case_id=case_id,
        session_id=session_id,
        hop=hop,
        latency_ms=int((time.perf_counter() - started) * 1000),
        llm_calls=gemini.usage.llm_calls,
        tokens_in=gemini.usage.tokens_in,
        tokens_out=gemini.usage.tokens_out,
        cache_hit=state.get("cache_hit"),
        **extra,
    )


def route_after_cache_hc2(state: HealthcareVectorState, *, agents: List[str]) -> str:
    """
    Facts cache hit → skip to first judgment hop for pipeline depth (not writer replay).

    Miss → cold path from first agent (intake).
    """
    case_id, session_id = _trace_ids(state)
    if state.get("cache_hit") and state.get("cache_facts"):
        route = first_judgment_hop_after_cache(state, agents)
    else:
        route = agents[0]
    trace_event(
        "route_after_cache",
        case_id=case_id,
        session_id=session_id,
        route=route,
        cache_hit=state.get("cache_hit"),
        cache_decision=state.get("cache_decision"),
        has_retrieved=bool(state.get("retrieved")),
        cache_facts=bool(state.get("cache_facts")),
    )
    return route


def _envelope_update(
    runtime: FinanceRuntime,
    hop: str,
    artifact: Dict[str, Any],
    *,
    state: Optional[HealthcareVectorState] = None,
    skip_embed: bool = False,
) -> Dict[str, Any]:
    """D2: reuse ingress raw_384; skip re-embed on cache-hit fast path."""
    if runtime.cache is None:
        return {}
    case_id, session_id = _trace_ids(state or {})
    raw_arr = raw_from_state(state) if state else None
    if skip_embed and raw_arr is not None:
        _, envelope = project_from_raw(runtime.cache, raw_arr)
        embed_mode = "reuse_ingress"
    else:
        _, envelope = project_text(runtime.cache, compact_json(artifact), raw_384=raw_arr)
        embed_mode = "reuse_raw" if raw_arr is not None else "full_embed"
    store_envelope_artifact(runtime, envelope.envelope_id, artifact)
    trace_event(
        "envelope_write",
        case_id=case_id,
        session_id=session_id,
        hop=hop,
        envelope_id=envelope.envelope_id,
        embed_mode=embed_mode,
        artifact_keys=sorted(artifact.keys()),
    )
    return {
        "prism_sequence": [envelope],
        "latest_envelope_id": envelope.envelope_id,
        "vector_hops": [
            {"hop": hop, "vector_dim": len(envelope.vector), "envelope_id": envelope.envelope_id}
        ],
    }


def _structured(gemini: InstrumentedGeminiClient, system: str, user: str) -> Dict[str, Any]:
    return parse_json_object(gemini.generate(system, user))


def make_hc2_nodes(gemini: InstrumentedGeminiClient, runtime: FinanceRuntime) -> Dict[str, Any]:
    retrieve_core = make_healthcare_retrieve_handler(runtime, topic="clinical_guidelines", top_k=6)

    def intake_node(state: HealthcareVectorState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        case = state["case"]
        artifact = _structured(gemini, INTAKE_D_SYSTEM, case.presentation)
        if not artifact.get("drugs") and case.drugs:
            artifact["drugs"] = list(case.drugs)
        if not artifact.get("topic") and case.topic:
            artifact["topic"] = case.topic
        hop_artifacts = dict(state.get("hop_artifacts") or {})
        hop_artifacts["intake"] = artifact
        out = {
            "drugs": list(artifact.get("drugs") or case.drugs or []),
            "topic": str(artifact.get("topic") or case.topic or ""),
            "last_artifact": artifact,
            "hop_artifacts": hop_artifacts,
            "intake_summary": str(artifact.get("facts") or ""),
            **_envelope_update(runtime, "intake", artifact, state=state),
            **_record_hop(state, "intake", started, gemini),
        }
        _hop_trace(state, "intake", started, gemini)
        return out

    def retrieve_node(state: HealthcareVectorState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        case = state["case"]
        hop_artifacts = dict(state.get("hop_artifacts") or {})
        topic = str(state.get("topic") or case.topic or "")
        retrieve_update = retrieve_core(
            {
                "message": case.presentation,
                "query": case.presentation,
                "topic": topic,
                "category_slug": topic,
                "query_vector_64": state.get("query_vector_64"),
            }
        )
        docs = list(retrieve_update.get("retrieved") or [])
        user = retrieve_handoff_plain(hop_artifacts, docs)
        artifact = _structured(gemini, RETRIEVE_D_SYSTEM, user)
        if not artifact.get("cited_ids"):
            artifact["cited_ids"] = [str(d.get("id") or "") for d in docs if d.get("id")]
        cats = sorted(
            {
                str(d.get("category_slug") or d.get("prismrag_category") or "")
                for d in docs
                if d.get("category_slug") or d.get("prismrag_category")
            }
        )
        if cats:
            artifact["category_slugs"] = cats
        elif assign_clinical_category(f"{topic} {case.presentation}"):
            artifact["category_slugs"] = [assign_clinical_category(f"{topic} {case.presentation}")]
        artifact["summary"] = str(artifact.get("summary") or "")
        hop_artifacts["retrieve"] = artifact
        out = {
            "retrieved": docs,
            "last_artifact": artifact,
            "hop_artifacts": hop_artifacts,
            **_envelope_update(runtime, "retrieve", artifact, state=state),
            **_record_hop(state, "retrieve", started, gemini, tools=1),
        }
        _hop_trace(state, "retrieve", started, gemini, tools=1)
        return out

    def analyze_node(state: HealthcareVectorState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        hop_artifacts = dict(state.get("hop_artifacts") or {})
        user = analyze_handoff_plain(hop_artifacts)
        artifact = _structured(gemini, ANALYZE_D_SYSTEM, user)
        hop_artifacts["analyze"] = artifact
        out = {
            "analysis": str(artifact.get("reasoning") or ""),
            "last_artifact": artifact,
            "hop_artifacts": hop_artifacts,
            **_envelope_update(runtime, "analyze", artifact, state=state),
            **_record_hop(state, "analyze", started, gemini),
        }
        _hop_trace(state, "analyze", started, gemini)
        return out

    def drug_node(state: HealthcareVectorState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        hop_artifacts = dict(state.get("hop_artifacts") or {})
        drugs = list(state.get("drugs") or [])
        interactions = check_drug_interactions(drugs) if drugs else []
        user = drug_handoff_plain(hop_artifacts, interactions)
        artifact = _structured(gemini, DRUG_D_SYSTEM, user)
        if not artifact.get("interactions"):
            artifact["interactions"] = interactions
        hop_artifacts["drug_check"] = artifact
        out = {
            "interactions": interactions,
            "last_artifact": artifact,
            "hop_artifacts": hop_artifacts,
            **_envelope_update(runtime, "drug_check", artifact, state=state),
            **_record_hop(state, "drug_check", started, gemini, tools=1 if drugs else 0),
        }
        _hop_trace(state, "drug_check", started, gemini, tools=1 if drugs else 0)
        return out

    def safety_node(state: HealthcareVectorState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        hop_artifacts = dict(state.get("hop_artifacts") or {})
        user = safety_handoff_plain(hop_artifacts)
        verdict = _structured(gemini, SAFETY_D_SYSTEM, user)
        abstained = should_abstain(
            case_topic=str(state.get("topic") or state["case"].topic or ""),
            retrieve_artifact=hop_artifacts.get("retrieve"),
            retrieved_docs=list(state.get("retrieved") or []),
            safety_verdict=verdict,
        )
        artifact = {**verdict, "verdict": "ABSTAIN" if abstained else str(verdict.get("verdict") or "APPROVED")}
        hop_artifacts["safety"] = artifact
        out = {
            "safety_verdict": str(artifact.get("reason") or artifact.get("verdict") or ""),
            "abstained": abstained,
            "last_artifact": artifact,
            "hop_artifacts": hop_artifacts,
            **_envelope_update(runtime, "safety", artifact, state=state),
            **_record_hop(state, "safety", started, gemini),
        }
        _hop_trace(state, "safety", started, gemini, abstained=abstained)
        return out

    def writer_node(state: HealthcareVectorState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        case_id, session_id = _trace_ids(state)
        case = state["case"]
        depth = int(case.pipeline_depth)
        hop_artifacts = dict(state.get("hop_artifacts") or {})
        abstained = bool(state.get("abstained"))
        cache_hit = bool(state.get("cache_hit"))

        if abstained:
            response = "ABSTAIN: insufficient grounded evidence for a definitive recommendation."
            out = {
                "response": response,
                **_record_hop(state, "writer", started, gemini),
            }
            _hop_trace(state, "writer", started, gemini, abstained=True)
            return out

        retrieved = list(state.get("retrieved") or [])
        interactions = list(state.get("interactions") or [])

        if depth == 2:
            intake = state.get("intake_summary") or hop_artifacts.get("intake") or {}
            user = f"Intake:\n{intake}\n"
            system = WRITER_SHALLOW_D_SYSTEM
            mode = "depth2_intake"
        elif depth == 4:
            user = (
                f"Intake:\n{hop_artifacts.get('intake', {})}\n\n"
                f"Analysis:\n{state.get('analysis') or hop_artifacts.get('analyze', {})}\n\n"
                f"Guidelines:\n{retrieved}\n"
            )
            system = WRITER_MID_D_SYSTEM
            mode = "depth4_mid"
        elif depth < 6:
            user = (
                f"Analysis:\n{state.get('analysis') or hop_artifacts.get('analyze', {})}\n\n"
                f"Guidelines:\n{retrieved}\n\nInteractions:\n{interactions}\n"
            )
            system = HL2_WRITER_MID_SYSTEM
            mode = "hl2_style"
        else:
            user = writer_handoff_plain(
                hop_artifacts=hop_artifacts,
                retrieved=retrieved,
                abstained=abstained,
            )
            system = WRITER_D_SYSTEM
            mode = "cache_hit_plain" if cache_hit else "plain_handoff"
            trace_event(
                "writer_prompt",
                case_id=case_id,
                session_id=session_id,
                hop="writer",
                mode=mode,
                depth=depth,
            )
            response = gemini.generate(system, user)
            if runtime.cache is not None:
                fp = cache_fingerprint_key(state, case)
                seed_healthcare_cache(
                    runtime,
                    cache_query_key(case),
                    build_cache_payload(state, response=response),
                    extra_queries=cache_seed_phrases(case),
                    pipeline_depth=case.pipeline_depth,
                    session_id=session_id,
                    fingerprint_key=fp,
                    case=case,
                    trace_fn=lambda event, **kw: trace_event(event, case_id=case_id, session_id=session_id, **kw),
                )

            artifact = {"response": response[:500], "from_cache": False}
            out = {
                "response": response,
                **_envelope_update(
                    runtime,
                    "writer",
                    artifact,
                    state=state,
                    skip_embed=False,
                ),
                **_record_hop(state, "writer", started, gemini),
            }
            _hop_trace(state, "writer", started, gemini, response_len=len(response))
            return out

        trace_event(
            "writer_prompt",
            case_id=case_id,
            session_id=session_id,
            hop="writer",
            mode=mode,
            depth=depth,
        )
        response = gemini.generate(system, user)

        if runtime.cache is not None:
            fp = cache_fingerprint_key(state, case)
            seed_healthcare_cache(
                runtime,
                cache_query_key(case),
                build_cache_payload(state, response=response),
                extra_queries=cache_seed_phrases(case),
                pipeline_depth=case.pipeline_depth,
                session_id=session_id,
                fingerprint_key=fp,
                case=case,
                trace_fn=lambda event, **kw: trace_event(event, case_id=case_id, session_id=session_id, **kw),
            )

        artifact = {"response": response[:500], "from_cache": False}
        out = {
            "response": response,
            **_envelope_update(
                runtime,
                "writer",
                artifact,
                state=state,
                skip_embed=False,
            ),
            **_record_hop(state, "writer", started, gemini),
        }
        _hop_trace(state, "writer", started, gemini, response_len=len(response))
        return out

    return {
        "intake": intake_node,
        "retrieve": retrieve_node,
        "analyze": analyze_node,
        "drug_check": drug_node,
        "safety": safety_node,
        "writer": writer_node,
    }
