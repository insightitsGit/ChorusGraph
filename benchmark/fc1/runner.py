"""FC1 — ChorusGraph ReAct/AgentNode path (fair comparison to FL1)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from benchmark.measure import TaskMeasurement, score_task_success
from benchmark.shared.corpus_seed import finance_seed_mode, finance_seed_phrases
from benchmark.shared.instrumented_gemini import InstrumentedGeminiClient
from benchmark.workload import WorkloadTask
from chorusgraph.agents.policy import PlanPolicy
from chorusgraph.examples.finance_agent.patterns_graph import (
    TENANT_ID,
    build_react_graph,
    pattern_initial_state,
)
from chorusgraph.examples.finance_agent.runtime import FinanceRuntime

# H9 fairness: B MUST use LLM ReAct/AgentNode, not regex researcher (BENCHMARK.md checklist).
FC1_REASONING_PATH = "react_agent/AgentNode"
BENCHMARK_CORTEX_ROOT = Path(".chorusgraph/benchmark_sessions")


def _task_success(result: Dict[str, Any], task: WorkloadTask) -> bool:
    return score_task_success(
        message=task.message,
        answer=result.get("response") or "",
        error=result.get("error"),
        validation=result.get("validation"),
        canonical_id=task.canonical_id,
        tool_result=result.get("tool_result"),
        variant=task.variant,
    )


def _cache_seed_phrases(task: WorkloadTask, *, seed_all_canonical: bool) -> List[str]:
    return finance_seed_phrases(
        task.canonical_id,
        mode=finance_seed_mode(seed_all_canonical=seed_all_canonical),
    )


class FC1Runner:
    """ChorusGraph ReAct graph — cache + Cortex + AgentNode, one runtime per session."""

    def __init__(self, *, seed_all_canonical_phrases: bool = True) -> None:
        self._seed_all_canonical_phrases = seed_all_canonical_phrases
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
            runtime = FinanceRuntime(tenant_id=TENANT_ID, gemini=gemini, cortex_cache_dir=str(cortex_dir))
            compiled, rt = build_react_graph(
                runtime,
                policy=PlanPolicy(max_steps=6),
            )
            self._sessions[key] = (compiled, rt)
        return self._sessions[key]

    def run(self, task: WorkloadTask) -> TaskMeasurement:
        compiled, runtime = self._session_graph(task)
        gemini = runtime.gemini
        assert gemini is not None and hasattr(gemini, "usage") and hasattr(gemini, "reset_usage")
        gemini.reset_usage()

        history = self._histories.get(task.session_id, [])
        if task.cross_session_recall:
            history = []
            if runtime.cortex is not None:
                runtime.cortex.wait_for_digest(timeout=120)

        started = time.perf_counter()
        state = pattern_initial_state(
            task.message,
            conversation_history=history,
            canonical_id=task.canonical_id,
            cache_seed_phrases=_cache_seed_phrases(
                task,
                seed_all_canonical=self._seed_all_canonical_phrases,
            ),
        )
        try:
            result = compiled.invoke(state)
            latency_ms = int((time.perf_counter() - started) * 1000)
            if result.get("conversation_history") and not task.cross_session_recall:
                self._histories[task.session_id] = list(result["conversation_history"])
            response = result.get("response") or ""
            if response.strip() and runtime.cortex is not None:
                runtime.schedule_turn_digest(task.message, response, turn_id=task.task_id)
                if task.variant == "memory_seed":
                    runtime.cortex.wait_for_digest(timeout=120)
            usage = gemini.usage
            grounding = result.get("memory_confidence")
            agent_trace = result.get("agent_trace") or []
            has_react = any(
                isinstance(s, dict) and "react" in str(s.get("kind", "")).lower()
                for s in agent_trace
            ) or bool(result.get("tool_calls"))
            return TaskMeasurement(
                task_id=task.task_id,
                session_id=task.session_id,
                container="FC1",
                message=task.message,
                variant=task.variant,
                latency_ms=latency_ms,
                llm_calls=usage.llm_calls,
                tokens_in=usage.tokens_in,
                tokens_out=usage.tokens_out,
                cost_usd=usage.cost_usd,
                task_success=_task_success({**result, "message": task.message}, task),
                answer=(result.get("response") or "")[:2000],
                cache_hit=result.get("cache_hit"),
                cache_score=result.get("cache_score"),
                cache_coarse_score=result.get("cache_coarse_score"),
                cache_verify_score=result.get("cache_verify_score"),
                grounding_score=float(grounding) if grounding is not None else None,
                tool_calls=len(result.get("tool_calls") or []),
                reasoning_path=FC1_REASONING_PATH if (has_react or result.get("cache_hit")) else "unknown",
                memory_cortex_group=task.memory_cortex_group,
                cross_session_recall=task.cross_session_recall or None,
                category_slug=task.category_slug,
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            usage = gemini.usage
            return TaskMeasurement(
                task_id=task.task_id,
                session_id=task.session_id,
                container="FC1",
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
                cache_coarse_score=None,
                cache_verify_score=None,
                grounding_score=None,
                error=str(exc),
                tool_calls=0,
                reasoning_path=FC1_REASONING_PATH,
                memory_cortex_group=task.memory_cortex_group,
                cross_session_recall=task.cross_session_recall or None,
                category_slug=task.category_slug,
            )
