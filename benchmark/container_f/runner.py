"""Container F — ChorusGraph finance multi-agent runner."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from benchmark.container_f.nodes import BENCHMARK_CORTEX_ROOT, TENANT_ID, build_finance_graph_f
from benchmark.measure import TaskMeasurement, score_task_success
from benchmark.shared.instrumented_gemini import InstrumentedGeminiClient
from benchmark.workload import CANONICAL_QUERIES, WorkloadTask
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime

F_REASONING_PATH = "finance_multiagent/envelope+cache_gate"


def _cache_seed_phrases(task: WorkloadTask) -> List[str]:
    cid = task.canonical_id
    if not cid or cid.startswith("memory_"):
        return []
    return list(CANONICAL_QUERIES.get(cid, []))


class ContainerFRunner:
    """ChorusGraph finance multi-agent — vector ingress + cache gate + envelope hops."""

    def __init__(self, *, seed_all_canonical_phrases: bool = True) -> None:
        self._seed_all_canonical = seed_all_canonical_phrases
        self._sessions: Dict[str, tuple[Any, FinanceRuntime]] = {}
        self._histories: Dict[str, List[Dict[str, str]]] = {}

    @staticmethod
    def _cortex_dir(task: WorkloadTask) -> Path:
        return BENCHMARK_CORTEX_ROOT / (task.memory_cortex_group or task.session_id)

    def _graph_key(self, task: WorkloadTask) -> str:
        return f"{task.session_id}|{self._cortex_dir(task)}"

    def _session_graph(self, task: WorkloadTask):
        key = self._graph_key(task)
        if key not in self._sessions:
            gemini = InstrumentedGeminiClient()
            cortex_dir = self._cortex_dir(task)
            runtime = FinanceRuntime(
                tenant_id=TENANT_ID,
                gemini=gemini,
                cortex_cache_dir=str(cortex_dir),
            )
            compiled, _, rt = build_finance_graph_f(runtime=runtime, gemini=gemini)
            self._sessions[key] = (compiled, rt)
        return self._sessions[key]

    def run(self, task: WorkloadTask) -> TaskMeasurement:
        compiled, runtime = self._session_graph(task)
        gemini = runtime.gemini
        assert gemini is not None and hasattr(gemini, "reset_usage")
        gemini.reset_usage()
        runtime.session_tool_cache.clear()

        history = self._histories.get(task.session_id, [])
        if task.cross_session_recall:
            history = []
            if runtime.cortex is not None:
                runtime.cortex.wait_for_digest(timeout=120)

        started = time.perf_counter()
        try:
            result = compiled.invoke(
                {
                    "task": task,
                    "message": task.message,
                    "conversation_history": history,
                    "tool_calls": [],
                    "tool_results": [],
                    "hop_metrics": [],
                    "vector_hops": [],
                    "prism_sequence": [],
                    "cache_seed_phrases": _cache_seed_phrases(task) if self._seed_all_canonical else [],
                }
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            if result.get("conversation_history") and not task.cross_session_recall:
                self._histories[task.session_id] = list(result["conversation_history"])

            response = result.get("response") or ""
            if response.strip() and runtime.cortex is not None:
                runtime.schedule_turn_digest(task.message, response, turn_id=task.task_id)
                if task.variant == "memory_seed":
                    runtime.cortex.wait_for_digest(timeout=120)

            hop_metrics = list(result.get("hop_metrics") or [])
            llm_calls = sum(h.llm_calls for h in hop_metrics)
            tokens_in = sum(h.tokens_in for h in hop_metrics)
            tokens_out = sum(h.tokens_out for h in hop_metrics)
            embed_count = len(result.get("prism_sequence") or [])

            return TaskMeasurement(
                task_id=task.task_id,
                session_id=task.session_id,
                container="F",
                message=task.message,
                variant=task.variant,
                latency_ms=latency_ms,
                llm_calls=llm_calls,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=(tokens_in * 0.15 + tokens_out * 0.60) / 1_000_000,
                task_success=score_task_success(
                    message=task.message,
                    answer=response,
                    error=result.get("error"),
                    validation=result.get("validation"),
                    canonical_id=task.canonical_id,
                    tool_result=result.get("tool_result"),
                    variant=task.variant,
                ),
                answer=response[:2000],
                cache_hit=result.get("cache_hit"),
                cache_score=result.get("cache_score"),
                cache_coarse_score=result.get("cache_coarse_score"),
                cache_verify_score=result.get("cache_verify_score"),
                tool_calls=len(result.get("tool_calls") or []),
                reasoning_path=F_REASONING_PATH,
                category_slug=task.category_slug,
                memory_cortex_group=task.memory_cortex_group,
                cross_session_recall=task.cross_session_recall or None,
                hop_metrics=[h.__dict__ for h in hop_metrics],
                embed_count=embed_count,
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            usage = gemini.usage
            return TaskMeasurement(
                task_id=task.task_id,
                session_id=task.session_id,
                container="F",
                message=task.message,
                variant=task.variant,
                latency_ms=latency_ms,
                llm_calls=usage.llm_calls,
                tokens_in=usage.tokens_in,
                tokens_out=usage.tokens_out,
                cost_usd=usage.cost_usd,
                task_success=False,
                answer="",
                error=str(exc),
                tool_calls=0,
                reasoning_path=F_REASONING_PATH,
                category_slug=task.category_slug,
                memory_cortex_group=task.memory_cortex_group,
                cross_session_recall=task.cross_session_recall or None,
            )
