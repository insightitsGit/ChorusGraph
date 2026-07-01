# Handoff 4 — End-to-End System on a Real Finance Graph (function-first)

**From:** Architect (Claude) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Design reference:** [`../docs/DESIGN_v0.2.md`](../docs/DESIGN_v0.2.md) §7.1 (nodes), §7.6 (patterns), §7.7 (role-typed nodes).
**Return in:** `handoffs/handoffback4.md`.

---

## 0. Operating rules
No fakes — real `prismlang`/`prismcache`, **real Gemini**, real tool calls. **Function-first: this
handoff proves the system WORKS end-to-end and returns correct answers. NO performance, latency,
cost, traffic, load, or false-positive measurement in this handoff** — that all belongs to the future
A/B benchmark, not here. If you're tempted to measure speed/cost, stop and note it for the benchmark.

## 1. Goal

A **real finance-domain agentic graph** runs the full ChorusGraph pipeline end-to-end and returns
**correct answers**, with the `tool` node and a role-typed node scaffold in place. This working system
becomes **Container B** for the eventual A/B benchmark. Success = "it works and is correct," nothing
about how fast or cheap.

## 2. Deliverables (scope)

### 2.1 `tool` node — `chorusgraph/nodes/tool.py`
First-class tool-calling primitive: typed signature, timeout + retry, side-effect isolation, result
flows back into state. Wire **at least one real finance tool** (a real market-data / FX / rate lookup
API, or a real deterministic financial calc) — **not a mock**.

### 2.2 Role-typed node scaffold — `chorusgraph/nodes/roles.py`
Base `Node` + role variants `ResearcherNode` / `WriterNode` / `ValidatorNode` per DESIGN §7.7.
Composition (Node + attachable role template: prompt, allowed tools, output schema); every variant
IS-A `Node`. A plain `Node` is promotable to a role. Keep it minimal but real.

### 2.3 A real finance agentic graph — `chorusgraph/examples/finance_agent/`
Assemble existing pieces (adapter + Route Ledger + sections + `cache_gate` used *functionally*) with
the `tool` node and role nodes into one runnable graph. Example task: *answer a finance question using
retrieval + a live-data tool, drafted by a `WriterNode`, checked by a `ValidatorNode`.* Real Gemini as
the controller.

**Make it conversation-state-aware** — carry a thread/conversation state (e.g. `conversation_history`)
so the graph is multi-turn-ready. Demo a short **2-turn** exchange where turn 2 references turn 1,
using in-run state only (no checkpointer yet). H5 will persist this same state (PrismCheckpointer +
Cortex) — building it thread-shaped now means H5 drops in without a rewrite. This is the "agent
remembers" headline in embryo; the durable version is H5.

### 2.4 End-to-end demonstration
Run the graph on a handful of **real** finance questions with real Gemini; show correct answers and
the Route Ledger capturing the full path (nodes, edges, tool call, rule_chain).

## 3. Explicitly OUT of scope
- **ANY performance / latency / cost / traffic / load / FP measurement** — deferred to the A/B benchmark.
- Live cache serving or cost claims (cache is used *functionally* only — it stores/retrieves, that's it).
- Execution patterns ReAct / Reflection / Plan-Solve (H5) — the role scaffold is enough for now.
- PrismCheckpointer, HITL, Cortex, native engine/DSL.

## 4. Acceptance criteria
- [ ] The finance graph runs **end-to-end** and returns **correct answers** on real finance questions (real Gemini).
- [ ] The `tool` node executes a **real** tool and its result flows into the final answer.
- [ ] At least one role node (e.g. `ValidatorNode`) demonstrably runs in the graph.
- [ ] The graph carries conversation state; a 2-turn demo shows turn 2 correctly using turn-1 context (in-run; durable persistence is H5).
- [ ] The Route Ledger logs the full path (including the tool call).
- [ ] No mocks/fakes anywhere; `pytest` green.
- [ ] **No performance numbers reported** — this is a functional milestone by design.

## 5. Open questions to answer in handoffback4
1. Which finance tool/data source did you wire, and why?
2. Did the cache mechanically hit within a session (functional check only — not a measurement)?
3. Any awkwardness assembling the pieces into one graph? What did the design get wrong?
4. Proposed H5 scope (execution patterns on top of this).

## 6. Return format
Same as prior: summary · file tree · how to run · real end-to-end run output (paste a real Q→A with
the ledger path) · decisions/deviations · blockers · answers to §5 · design contradictions · proposed H5 scope.

---
*Handoff 4 · architect: Claude · function-first · end-to-end finance graph = future Container B · NO perf/cost measurement.*
