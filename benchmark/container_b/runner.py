"""Container B task runner — ChorusGraph finance agent + shared measurement."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from benchmark.measure import TaskMeasurement, score_task_success
from benchmark.shared.instrumented_gemini import InstrumentedGeminiClient
from benchmark.thresholds import measured_thresholds
from benchmark.workload import WorkloadTask
from chorusgraph.examples.finance_agent.graph import TENANT_ID, build_finance_graph, initial_state
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime


def _task_success(result: Dict[str, Any]) -> bool:
    return score_task_success(
        message=result.get("message") or "",
        answer=result.get("response") or "",
        error=result.get("error"),
        validation=result.get("validation"),
    )


class ContainerBRunner:
    """One FinanceRuntime per session so semantic cache repeats are observable."""

    def __init__(self) -> None:
        self._thresholds = measured_thresholds()
        self._sessions: Dict[str, tuple[Any, FinanceRuntime]] = {}
        self._histories: Dict[str, List[Dict[str, str]]] = {}

    def _session_graph(self, session_id: str):
        if session_id not in self._sessions:
            gemini = InstrumentedGeminiClient()
            runtime = FinanceRuntime(tenant_id=TENANT_ID, gemini=gemini)
            compiled, rt = build_finance_graph(
                runtime,
                coarse_threshold=self._thresholds.coarse,
                verify_threshold=self._thresholds.verify_for("fx_rates"),
            )
            self._sessions[session_id] = (compiled, rt)
        return self._sessions[session_id]

    def run(self, task: WorkloadTask) -> TaskMeasurement:
        compiled, runtime = self._session_graph(task.session_id)
        gemini = runtime.gemini
        assert isinstance(gemini, InstrumentedGeminiClient)
        gemini.reset_usage()

        history = self._histories.get(task.session_id, [])
        started = time.perf_counter()
        state = initial_state(task.message, conversation_history=history)
        try:
            result = compiled.invoke(state)
            latency_ms = int((time.perf_counter() - started) * 1000)
            if result.get("conversation_history"):
                self._histories[task.session_id] = list(result["conversation_history"])
            usage = gemini.usage
            grounding = result.get("memory_confidence")
            return TaskMeasurement(
                task_id=task.task_id,
                session_id=task.session_id,
                container="B",
                message=task.message,
                variant=task.variant,
                latency_ms=latency_ms,
                llm_calls=usage.llm_calls,
                tokens_in=usage.tokens_in,
                tokens_out=usage.tokens_out,
                cost_usd=usage.cost_usd,
                task_success=_task_success({**result, "message": task.message}),
                answer=(result.get("response") or "")[:2000],
                cache_hit=result.get("cache_hit"),
                cache_score=result.get("cache_score"),
                grounding_score=float(grounding) if grounding is not None else None,
                tool_calls=len(result.get("tool_calls") or []),
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            usage = gemini.usage
            return TaskMeasurement(
                task_id=task.task_id,
                session_id=task.session_id,
                container="B",
                message=task.message,
                variant=task.variant,
                latency_ms=latency_ms,
                llm_calls=usage.llm_calls,
                tokens_in=usage.tokens_in,
                tokens_out=usage.tokens_out,
                cost_usd=usage.cost_usd,
                task_success=False,
                answer="",
                cache_hit=None,
                cache_score=None,
                grounding_score=None,
                error=str(exc),
                tool_calls=0,
            )
