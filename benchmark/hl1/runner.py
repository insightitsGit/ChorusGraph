"""HL1 runner — LangGraph single-agent healthcare."""

from __future__ import annotations

from typing import Any, Dict

from benchmark.hl1.graph import build_healthcare_react_graph_hl1, run_healthcare_case
from benchmark.healthcare_workload import HealthcareCase
from benchmark.multiagent_measure import MultiAgentMeasurement, score_healthcare_answer


class HL1Runner:
    """LangGraph single-agent healthcare ReAct."""

    def __init__(self) -> None:
        self.compiled, self.gemini = build_healthcare_react_graph_hl1()

    def run(self, case: HealthcareCase) -> MultiAgentMeasurement:
        result = run_healthcare_case(case, compiled=self.compiled, gemini=self.gemini)
        usage = result.get("_llm_usage")
        answer = result.get("response") or ""
        abstained = bool(result.get("abstained"))
        return MultiAgentMeasurement(
            case_id=case.case_id,
            container="HL1",
            pipeline_depth=case.pipeline_depth,
            message=case.presentation,
            latency_ms=int(result.get("_latency_ms") or 0),
            llm_calls=usage.llm_calls if usage else 0,
            tokens_in=usage.tokens_in if usage else 0,
            tokens_out=usage.tokens_out if usage else 0,
            cost_usd=usage.cost_usd if usage else 0.0,
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
            error=result.get("error"),
        )


__all__ = ["HL1Runner"]
