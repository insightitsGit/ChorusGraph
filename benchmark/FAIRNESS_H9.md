# H9 Fairness Verification — Pre-Run Checklist

**Verified before any volume run (Handoff 9 §2.1).**

## 1. B reasons comparably to A (LLM ReAct path)

| Check | Status |
|-------|--------|
| Container A uses LangGraph ReAct JSON loop | ✅ `benchmark/container_a/graph.py` |
| Container B uses ChorusGraph `Agent(pattern="react")` via `AgentNode` | ✅ `build_react_graph()` + `make_react_agent_handler` |
| Container B does **NOT** use regex `researcher` node | ✅ `ContainerBRunner` switched from `build_finance_graph` to `build_react_graph` |
| B reasoning path constant | ✅ `B_REASONING_PATH = "react_agent/AgentNode"` recorded on each measurement |
| Same ReAct system prompt text | ✅ Both use `benchmark/shared/prompts.py` / `REACT_SYSTEM` |

**Residual asymmetry (disclosed):** B adds `cache_gate` + Cortex + optional reflection validator (max 1 pass). A has no cache. Graph depth differs by one cache node — this is the intended product delta.

## 2. Rubric scores on answer content

| Check | Status |
|-------|--------|
| Shared `score_task_success()` in `benchmark/measure.py` | ✅ |
| Applied identically in Container A and B runners | ✅ |
| FX/compound queries require numeric answer (`\d+\.\d+`) | ✅ |
| Does **not** penalize correct answers for `tool_calls=0` | ✅ (H8 fix retained) |
| Validation `approved=False` fails task | ✅ |

## 3. Sign-off

Both fairness fixes confirmed **before** volume run. The A↔B delta isolates ChorusGraph cache/memory layer vs LangGraph baseline, not regex-vs-LLM routing.

---
*H9 pre-run · architect requirement · do not run until both rows above are green.*
