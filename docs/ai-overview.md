# AI / LLM context — ChorusGraph

> Concise reference for humans and coding assistants.  
> Do not invent APIs beyond this file and `chorusgraph/`. Package: **`chorusgraph` 1.1.0**, import **`chorusgraph`**.

---

## 10-sentence project summary

1. ChorusGraph is an Apache-2.0 native agent-graph runtime (`pip install chorusgraph`) — **not** a LangGraph wrapper.  
2. You build graphs with `chorusgraph.core.Graph`, `START`, `END`, and compile with a `ChorusStack`.  
3. `ChorusStack.defaults(tenant_id=...)` attaches semantic cache, retrieval, memory, ledger, and tools via swappable ports.  
4. Product path has **no LangGraph dependency**; LangGraph appears only in optional benchmark baselines.  
5. L1 semantic cache skips repeated / paraphrased LLM hops when configured.  
6. L2 retrieval is a `RetrievalBackend` port (keyword default; PrismRAG / vector opt-in); 1.1.0 adds optional warm chunk vectors (`warm_retrieval`).  
7. Route Ledger records auditable `rule_chain` hops for explainability.  
8. CLIs: `chorusgraph-demo`, `chorusgraph-audit`, finance pattern demos (API key for some).  
9. Competes with LangGraph as an orchestration runtime; does **not** replace vector databases as a category.  
10. Limitations: bring your own LLM keys for generative demos; enterprise Postgres persistence may be license-gated; warm vectors are opt-in.

---

## Core concepts

| Term | Definition |
|------|------------|
| **Graph** | Native BSP graph builder: nodes, edges, `compile()` |
| **ChorusStack** | Composition object — cache / memory / tools / retrieval ports |
| **Envelope** | Per-hop publish unit (artifact + optional vectors / category) |
| **Route Ledger** | Audit trail of routing decisions |
| **L1 cache** | Semantic cache for repeat/paraphrase skip |
| **L2 retrieval** | Knowledge retrieve port; optional warm chunk vectors (ADR-005) |
| **warm_retrieval** | Boot-time warm of partition index for query-only retrieve |

---

## Key APIs

```python
from chorusgraph import Graph, START, END, ChorusStack
from chorusgraph.core.node import dict_node_adapter

stack = ChorusStack.defaults(tenant_id="demo")
# Optional: .with_retrieval(...), .with_cache(...), stack.warm_retrieval(partition="...")

g = Graph(tenant_id="demo", graph_id="hello")
g.add_node("echo", dict_node_adapter(lambda s: {"reply": f"Hello, {s.get('name', 'world')}"}, hop="echo"))
g.add_edge(START, "echo")
g.add_edge("echo", END)
out = g.compile(stack=stack).invoke({"name": "ChorusGraph"})
```

See also: [AI_IDE_PROMPTS.md](AI_IDE_PROMPTS.md) · [COMPOSE.md](COMPOSE.md) · [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md).

---

## Common use cases

1. Production agent workflows with cache + audit in one runtime.  
2. Finance / healthcare multi-hop agents with published A/B benches vs LangGraph.  
3. RAG agents that should not re-embed the corpus every turn (warm L2).  
4. Teams who want LangGraph-comparable orchestration without LangGraph on the product path.

---

## Migration guidance

From **LangGraph**: rebuild the graph on `chorusgraph.core.Graph` (nodes/edges/conditionals); attach `ChorusStack` for cache/retrieval/memory. Use [AI_IDE_PROMPTS.md](AI_IDE_PROMPTS.md) Prompt 2 for assisted migration. From **DIY** (orchestrator + Redis + vector DB + logs): map each concern to a `ChorusStack` port instead of glue services. CrewAI and similar: manual translation — no automated adapter claimed.

---

## Limitations / when NOT to use

- You only need a thin LangGraph wrapper and want to stay on LangGraph APIs forever.  
- You need a standalone vector DB product (use your DB; ChorusGraph retrieves via a port).  
- You refuse any Prism/ChorusStack composition and want orchestration-only with zero defaults.  
- Benchmark extras (`[benchmark]`) are for comparison runs, not required for product path.

---

## Frequently compared projects

| Project | Relationship | Prefer ChorusGraph when… | Prefer them when… |
|---------|--------------|--------------------------|-------------------|
| LangGraph | Alternative runtime | Native stack + cache/ledger/retrieval ports | You are standardized on LangGraph ecosystem |
| CrewAI / AutoGen | Different agent frameworks | Graph + Prism ports + benches | Multi-agent role frameworks fit better |
| Plain FastAPI + tools | DIY | You want graph runtime + audit | Simple single-call apps |

---

## Links

| Path | Role |
|------|------|
| [ai-overview.md](ai-overview.md) | This file |
| [llm-context.md](llm-context.md) | Alias |
| [architecture.md](architecture.md) | Stack diagram |
| [AI_IDE_PROMPTS.md](AI_IDE_PROMPTS.md) | Cursor install prompts |
| [COMPOSE.md](COMPOSE.md) | ChorusStack |
| [BENCHMARK_RESULTS.md](BENCHMARK_RESULTS.md) | Published A/B |
| ../README.md | Human README |
