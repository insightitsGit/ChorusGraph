"""Container A task runner — maps graph output to shared measurement schema."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from benchmark.container_a.graph import build_langgraph_agent, run_task
from benchmark.measure import TaskMeasurement, score_task_success
from benchmark.workload import WorkloadTask


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


class ContainerARunner:
    def __init__(self) -> None:
        self.compiled, self.gemini, self._checkpointer = build_langgraph_agent()
        self._histories: Dict[str, List[Dict[str, str]]] = {}

    def run(self, task: WorkloadTask) -> TaskMeasurement:
        history = self._histories.get(task.session_id, [])
        if task.cross_session_recall:
            history = []
        result = run_task(
            task.message,
            compiled=self.compiled,
            gemini=self.gemini,
            thread_id=task.session_id,
            conversation_history=history,
        )
        if result.get("conversation_history") and not task.cross_session_recall:
            self._histories[task.session_id] = list(result["conversation_history"])

        usage = result.get("_llm_usage")
        return TaskMeasurement(
            task_id=task.task_id,
            session_id=task.session_id,
            container="A",
            message=task.message,
            variant=task.variant,
            latency_ms=int(result.get("_latency_ms") or 0),
            llm_calls=usage.llm_calls if usage else 0,
            tokens_in=usage.tokens_in if usage else 0,
            tokens_out=usage.tokens_out if usage else 0,
            cost_usd=usage.cost_usd if usage else 0.0,
            task_success=_task_success({**result, "message": task.message}, task),
            answer=(result.get("response") or "")[:2000],
            tool_calls=len(result.get("tool_calls") or []),
            error=result.get("error"),
            memory_cortex_group=task.memory_cortex_group,
            cross_session_recall=task.cross_session_recall or None,
            category_slug=task.category_slug,
        )
