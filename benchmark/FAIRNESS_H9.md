# H9/H10 Fairness Verification — Pre-Run Checklist

**Verified before volume runs (Handoff 9 §2.1, Handoff 10 §2.4).**

## 1. B reasons comparably to A (LLM ReAct path)

| Check | Status |
|-------|--------|
| Container A uses LangGraph ReAct JSON loop | ✅ `benchmark/container_a/graph.py` |
| Container B uses ChorusGraph `Agent(pattern="react")` via `AgentNode` | ✅ `build_react_graph()` + `make_react_agent_handler` |
| Container B does **NOT** use regex `researcher` node on the ReAct path | ✅ `ContainerBRunner` → `build_react_graph()` |
| B reasoning path constant | ✅ `B_REASONING_PATH = "react_agent/AgentNode"` |
| Same ReAct system prompt text | ✅ `benchmark/shared/prompts.py` / `REACT_SYSTEM` |

## 2. Rubric — canonical, grounded scoring (H10 §2.2)

| Check | Status |
|-------|--------|
| Shared `score_task_success()` in `benchmark/measure.py` | ✅ |
| Applied identically in Container A and B runners | ✅ |
| **`canonical_id` scoring** per task intent (FX pair, compound FV, compare) | ✅ `benchmark/rubric.py` |
| Compound: answer must include correct future value (~$11,614.72 ± tolerance) | ✅ |
| FX: answer must name correct currency pair **and** grounded rate | ✅ |
| Wrong-pair / session-leak answers no longer pass | ✅ (A false-pass rate drops under canonical rubric) |
| Validation `approved=False` fails task | ✅ |
| Does **not** penalize correct answers for `tool_calls=0` | ✅ |

Legacy rubric (any `\d+\.\d+` in answer) is **retired** when `canonical_id` is set on the task.

## 3. Disclosed product asymmetries (H10 §2.4 — Director resolution)

**Resolution:** Document as **ChorusGraph framework features**, not silent benchmark rigging.

Container B includes deterministic fast paths that Container A (pure LangGraph ReAct) does **not** implement:

| Feature | B behavior | A behavior | Competitive framing |
|---------|------------|------------|---------------------|
| **Template writer** | FX/compound drafts from tool payloads without LLM when data is complete | Always calls Gemini in `writer_node` | Productized “LLM only at the boundary” |
| **Compound fast path** | `cache_gate → compound_tool → writer` skips ReAct when `parse_compound_params()` matches | ReAct must discover `compound_interest` via LLM | Intent router + CPU tool |
| **cache_gate + semantic cache** | ONNX 64-d coarse + 384-d verify before ReAct | None | Core ChorusGraph delta |
| **Cortex structured recall** | `recall_structured()` on writer hop | None | Memory layer |
| **Reflection validator** | Up to 1 pass on B pattern graph | Validator on A | Optional quality gate |

**What the A/B delta isolates:** cache + memory + deterministic orchestration vs a competent LangGraph baseline — **not** “same code path with cache on/off.”

**What a skeptic should compare:** LangGraph + your own templates/routing (engineering effort) vs buying ChorusGraph’s integrated path.

## 4. Residual asymmetries (unchanged, intentional)

- B graph depth: `cache_gate` → (`compound_tool` \| `react_agent`) → `writer` → `validator`
- A graph depth: `react` → `tool` → `writer` → `validator`
- Cache hit benefit appears only when workload repeat rate exercises semantic cache (bands 40%/60%).

## 5. Sign-off

Fairness checklist green for **H10 volume run** (post-fix v0.9.1: compound routing + canonical rubric).

---
*H9/H10 · architect requirement · disclose asymmetry · canonical rubric · no silent wins.*
