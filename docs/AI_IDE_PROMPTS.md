# AI IDE Quickstart Prompts

Copy one of these into Cursor, Claude Code, Windsurf, Copilot Chat, or any AI coding assistant with
shell + file access. The assistant installs ChorusGraph, wires it into your project, and verifies it
runs — you don't type a single `pip` command yourself.

Both prompts are grounded in the real, current `chorusgraph` 1.0.1 API — nothing invented. Prompt 2 is
explicit about what's an automated migration (LangGraph) versus a manual-translation guide (CrewAI),
since no CrewAI adapter exists yet.

---

## Prompt 1 — Fresh install (new project or adding an agent to an existing one)

```
I want to add ChorusGraph (a native Python agent-graph runtime) to this project. Do the following:

1. Detect my Python environment/package manager (venv, poetry, uv, pipenv — whatever this repo uses)
   and install `chorusgraph` with it. If I mention I need document/RAG retrieval anywhere below, install
   `chorusgraph[retrieval]` instead (adds Chroma-backed vector search).

2. Verify the install actually works before writing any of my code:
   python -c "import chorusgraph; from chorusgraph import Graph, START, END, ChorusStack; print(chorusgraph.__version__)"
   If this fails, stop and show me the exact error — do not proceed on a broken install.

3. Ask me (in one short message) what my agent needs to do: what are the steps/tools involved, does it
   need to look anything up (retrieval), does it need to remember things across turns (memory), and do I
   want a semantic cache to avoid re-answering repeated questions. Wait for my answer before building.

4. Using my answer, scaffold a real `chorusgraph.core.Graph` for my use case — not a toy "hello world" —
   using this verified pattern as the skeleton:

   from chorusgraph import Graph, START, END, ChorusStack
   from chorusgraph.core.node import dict_node_adapter

   stack = ChorusStack.defaults(tenant_id="<pick a sensible tenant id for this project>")
   # Swap ports only if I asked for it:
   #   .with_retrieval(PrismRAGRetrievalBackend(...))   — from chorusgraph.compose, if I need vector RAG
   #   .with_cache(RedisCacheBackend(tenant_id=...))    — from chorusgraph.compose.adapters.redis_cache, if I asked for Redis

   g = Graph(tenant_id="<same tenant id>", graph_id="<name this after what the agent does>")
   g.add_node("<step_name>", dict_node_adapter(<my handler function>, hop="<step_name>"))
   # ... add_node per step I described, add_edge to connect them in order (or add_conditional_edges
   # if I described branching logic)
   g.add_edge(START, "<first step>")
   g.add_edge("<last step>", END)

   compiled = g.compile(stack=stack)
   out = compiled.invoke({...my actual input shape...})

5. Write each node's handler as a real function tied to what I described — do not stub with fake logic.
   If a step calls an LLM, use whatever LLM client this project already uses (or ask me which one if none
   exists yet). If a step needs a tool call, use `chorusgraph.nodes.tool.ToolRegistry`/`ToolSpec`.

6. Run it for real (not just import-check) and show me the actual output. If it errors, fix it and rerun
   — don't hand me broken code and call it done.

7. Tell me, in 3 bullets max: what you built, where the cache/retrieval/memory ports are so I can swap
   them later, and point me at docs/INSTALL.md and docs/PLUGINS.md (in the chorusgraph repo, or
   https://github.com/insightitsGit/ChorusGraph/blob/master/docs/) for anything deeper.

Do not invent ChorusGraph APIs that don't exist — if you're unsure a method/class is real, check
`python -c "import chorusgraph; help(chorusgraph)"` or the installed package source before using it.
```

---

## Prompt 2 — Replace / migrate from LangGraph or CrewAI

```
This project currently uses [LangGraph / CrewAI — tell me which]. I want to move it onto ChorusGraph
(a native agent-graph runtime with a built-in semantic cache, retrieval, memory, and audit trail — not
a wrapper around LangGraph). Do the following:

STEP 1 — Detect what's actually here.
Search the repo for LangGraph usage (`from langgraph.graph import StateGraph`, `.add_node`, `.add_edge`,
`.compile()`, `langgraph.checkpoint`) or CrewAI usage (`from crewai import Agent, Task, Crew`,
`Crew(...).kickoff()`). Tell me which one you found and where, before changing anything.

──────────────────────────────────────────────────────────────────
IF LANGGRAPH — this is a real, automated migration path. Do this:
──────────────────────────────────────────────────────────────────

1. `pip install chorusgraph` (add `[retrieval]` if the graph does RAG/retrieval).
2. Verify: `python -c "import chorusgraph; from chorusgraph.compat.langgraph import compile_state_graph; print('ok')"`
3. Find the `StateGraph(...)` builder object BEFORE it's `.compile()`'d in my code (the object with
   `.add_node`/`.add_edge`/`.add_conditional_edges` already called on it, not yet compiled).
4. Replace the LangGraph `.compile()` call with the ChorusGraph shim:

   from chorusgraph.compat.langgraph import compile_state_graph
   compiled = compile_state_graph(my_existing_state_graph_builder)
   # compiled.invoke(...) / .stream(...) work the same way `.compile()`'s output did

5. Do NOT rewrite my nodes, edges, or business logic — the shim mirrors the existing builder onto the
   native ChorusGraph engine. The only change should be the compile step.
6. Run my existing tests (or write a quick before/after smoke test if none exist) and confirm identical
   output before and after the swap. If anything behaves differently, stop and show me the diff — don't
   silently paper over it.
7. Once it's running on the native engine, tell me about the semantic cache and Route Ledger it now has
   for free (things LangGraph doesn't give me), and point me at docs/CACHE_PROFILES.md and
   docs/PLUGINS.md for tuning them.

──────────────────────────────────────────────────────────────────
IF CREWAI — be honest with me: there is no automatic CrewAI adapter in ChorusGraph today. This is a
manual translation, not a one-line swap. Do this carefully:
──────────────────────────────────────────────────────────────────

1. `pip install chorusgraph` and verify it imports (see Prompt 1, step 2).
2. Map CrewAI concepts to ChorusGraph's real primitives, don't invent new ones:
   - Each CrewAI `Agent` (role, goal, backstory) → a ChorusGraph node bound with a `RoleTemplate` via
     `chorusgraph.nodes.roles` (`ResearcherNode`/`WriterNode`/`ValidatorNode` are built-in examples;
     use `promote(node, role="...")` for a custom role).
   - Each CrewAI `Task` (the work an agent does) → that node's handler function body.
   - The `Crew(agents=[...], tasks=[...]).kickoff()` sequence → an explicit `chorusgraph.core.Graph`:
     preserve the same task order as static `add_edge` chains; if CrewAI ran tasks in parallel, use
     ChorusGraph's `Send` (fan-out) instead of forcing them sequential.
3. Build the graph using the same skeleton as Prompt 1 step 4.
4. Before declaring this done, run BOTH the old CrewAI flow and the new ChorusGraph flow on the same
   input and show me they produce equivalent results. Do not assume the translation is correct — prove it.
5. Tell me plainly which parts of the original CrewAI behavior (if any) you were not able to verify are
   equivalent, rather than claiming a clean 1:1 migration if you're not sure.

In both cases: do not invent ChorusGraph APIs. Check `python -c "import chorusgraph; help(chorusgraph)"`
or the installed source if you're unsure whether something exists.
```

---

*Both prompts assume `chorusgraph>=1.0.1` (verified working via a clean-room `pip install` + hello-world
run). If a newer version changes these APIs, `docs/STABILITY.md` documents the deprecation policy — the
1.0 public surface is frozen, so these should keep working across patch/minor releases.*
