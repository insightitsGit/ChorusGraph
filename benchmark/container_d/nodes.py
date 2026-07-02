"""Container D role-typed nodes — envelope handoffs, bounded prompts per hop."""

from __future__ import annotations

import time
from typing import Any, Dict, List

from benchmark.container_c.runner import HealthcareState, _record_hop
from benchmark.container_d.artifacts import (
    bounded_docs,
    compact_analyze,
    compact_intake,
    compact_json,
    compact_retrieve,
    envelope_handoff,
    parse_json_object,
    safety_handoff_user,
    should_abstain,
    store_envelope_artifact,
    writer_handoff_user,
)
from benchmark.container_d.prompts import (
    ANALYZE_D_SYSTEM,
    DRUG_D_SYSTEM,
    INTAKE_D_SYSTEM,
    RETRIEVE_D_SYSTEM,
    SAFETY_D_SYSTEM,
    WRITER_D_SYSTEM,
)
from benchmark.healthcare.tools import check_drug_interactions, retrieve_guidelines
from benchmark.shared.instrumented_gemini import InstrumentedGeminiClient
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime
from chorusgraph.transforms.projector import project_text


def _envelope_update(runtime: FinanceRuntime, hop: str, artifact: Dict[str, Any]) -> Dict[str, Any]:
    """Project compact JSON artifact to Prism envelope and store for envelope_id resolution."""
    text = compact_json(artifact)
    if runtime.cache is None:
        return {}
    _, envelope = project_text(runtime.cache, text)
    store_envelope_artifact(runtime, envelope.envelope_id, artifact)
    return {
        "prism_sequence": [envelope],
        "latest_envelope_id": envelope.envelope_id,
        "vector_hops": [
            {
                "hop": hop,
                "vector_dim": len(envelope.vector),
                "envelope_id": envelope.envelope_id,
            }
        ],
    }


def _structured(gemini: InstrumentedGeminiClient, system: str, user: str) -> Dict[str, Any]:
    """Text-mode Gemini + JSON parse — same API settings as Container C."""
    return parse_json_object(gemini.generate(system, user))


def make_d_nodes(gemini: InstrumentedGeminiClient, runtime: FinanceRuntime) -> Dict[str, Any]:
    def intake_node(state: HealthcareState) -> Dict[str, Any]:
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
        return {
            "drugs": list(artifact.get("drugs") or case.drugs or []),
            "topic": str(artifact.get("topic") or case.topic or ""),
            "last_artifact": artifact,
            "hop_artifacts": hop_artifacts,
            "intake_summary": str(artifact.get("facts") or ""),
            **_envelope_update(runtime, "intake", artifact),
            **_record_hop(state, "intake", started, gemini),
        }

    def retrieve_node(state: HealthcareState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        case = state["case"]
        hop_artifacts = dict(state.get("hop_artifacts") or {})
        topic = str(state.get("topic") or case.topic or "")
        docs = retrieve_guidelines(topic, case.presentation)
        user = envelope_handoff(
            hop="retrieve",
            envelope_id=state.get("latest_envelope_id"),
            hop_input={
                "facts": compact_intake(hop_artifacts.get("intake")),
                "retrieved_docs": bounded_docs(docs),
            },
        )
        artifact = _structured(gemini, RETRIEVE_D_SYSTEM, user)
        if not artifact.get("cited_ids"):
            artifact["cited_ids"] = [str(d.get("id") or "") for d in docs if d.get("id")]
        artifact["summary"] = str(artifact.get("summary") or "")
        hop_artifacts = dict(state.get("hop_artifacts") or {})
        hop_artifacts["retrieve"] = artifact
        return {
            "retrieved": docs,
            "last_artifact": artifact,
            "hop_artifacts": hop_artifacts,
            **_envelope_update(runtime, "retrieve", artifact),
            **_record_hop(state, "retrieve", started, gemini, tools=1),
        }

    def analyze_node(state: HealthcareState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        hop_artifacts = dict(state.get("hop_artifacts") or {})
        user = envelope_handoff(
            hop="analyze",
            envelope_id=state.get("latest_envelope_id"),
            hop_input={
                "intake": compact_intake(hop_artifacts.get("intake")),
                "retrieve": compact_retrieve(hop_artifacts.get("retrieve")),
            },
        )
        artifact = _structured(gemini, ANALYZE_D_SYSTEM, user)
        hop_artifacts = dict(state.get("hop_artifacts") or {})
        hop_artifacts["analyze"] = artifact
        return {
            "analysis": str(artifact.get("reasoning") or ""),
            "last_artifact": artifact,
            "hop_artifacts": hop_artifacts,
            **_envelope_update(runtime, "analyze", artifact),
            **_record_hop(state, "analyze", started, gemini),
        }

    def drug_node(state: HealthcareState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        hop_artifacts = dict(state.get("hop_artifacts") or {})
        drugs = list(state.get("drugs") or [])
        interactions = check_drug_interactions(drugs) if drugs else []
        user = envelope_handoff(
            hop="drug_check",
            envelope_id=state.get("latest_envelope_id"),
            hop_input={
                "analyze": compact_analyze(hop_artifacts.get("analyze")),
                "interactions": interactions,
            },
        )
        artifact = _structured(gemini, DRUG_D_SYSTEM, user)
        if not artifact.get("interactions"):
            artifact["interactions"] = interactions
        hop_artifacts = dict(state.get("hop_artifacts") or {})
        hop_artifacts["drug_check"] = artifact
        return {
            "interactions": interactions,
            "last_artifact": artifact,
            "hop_artifacts": hop_artifacts,
            **_envelope_update(runtime, "drug_check", artifact),
            **_record_hop(state, "drug_check", started, gemini, tools=1 if drugs else 0),
        }

    def safety_node(state: HealthcareState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        hop_artifacts = dict(state.get("hop_artifacts") or {})
        user = safety_handoff_user(
            envelope_id=state.get("latest_envelope_id"),
            hop_artifacts=hop_artifacts,
        )
        verdict = _structured(gemini, SAFETY_D_SYSTEM, user)
        abstained = should_abstain(
            case_topic=str(state.get("topic") or state["case"].topic or ""),
            retrieve_artifact=hop_artifacts.get("retrieve"),
            retrieved_docs=list(state.get("retrieved") or []),
            safety_verdict=verdict,
        )
        artifact = {**verdict, "verdict": "ABSTAIN" if abstained else str(verdict.get("verdict") or "APPROVED")}
        hop_artifacts = dict(state.get("hop_artifacts") or {})
        hop_artifacts["safety"] = artifact
        return {
            "safety_verdict": str(artifact.get("reason") or artifact.get("verdict") or ""),
            "abstained": abstained,
            "last_artifact": artifact,
            "hop_artifacts": hop_artifacts,
            **_envelope_update(runtime, "safety", artifact),
            **_record_hop(state, "safety", started, gemini),
        }

    def writer_node(state: HealthcareState) -> Dict[str, Any]:
        started = time.perf_counter()
        gemini.reset_usage()
        if state.get("abstained"):
            response = "ABSTAIN: insufficient grounded evidence for a definitive recommendation."
            return {
                "response": response,
                **_record_hop(state, "writer", started, gemini),
            }
        hop_artifacts = dict(state.get("hop_artifacts") or {})
        user = writer_handoff_user(
            envelope_id=state.get("latest_envelope_id"),
            hop_artifacts=hop_artifacts,
        )
        response = gemini.generate(WRITER_D_SYSTEM, user)
        return {
            "response": response,
            **_record_hop(state, "writer", started, gemini),
        }

    return {
        "intake": intake_node,
        "retrieve": retrieve_node,
        "analyze": analyze_node,
        "drug_check": drug_node,
        "safety": safety_node,
        "writer": writer_node,
    }
