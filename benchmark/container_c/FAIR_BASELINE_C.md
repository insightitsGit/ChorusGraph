# Fair baseline audit — Container C (LangGraph multi-agent healthcare)

**Purpose:** Document that Container C is a **competent** LangGraph multi-agent build — not a rigged or broken baseline (cf. pre-H11 Container A).

## Pipeline (depth sweep)

| Depth | Agents | Tools invoked |
|-------|--------|---------------|
| 2 | intake → writer | None (short path) |
| 4 | intake → retrieve → analyze → writer | `retrieve_guidelines` at retrieve hop |
| 6 | intake → retrieve → analyze → drug_check → safety → writer | `retrieve_guidelines` + `check_drug_interactions` |

Implementation: `benchmark/container_c/runner.py` — linear LangGraph chain per depth (`PIPELINE_AGENTS` in `healthcare_workload.py`).

## Anti-A-bug gates

1. **Tools are called in code**, not left to LLM discretion — `retrieve_node` and `drug_node` invoke Python tools before the LLM summarizes results.
2. **Handoffs are real** — each agent node updates shared `HealthcareState` and passes accumulated context to the next hop (intake summary → retrieve → analyze → …).
3. **Safety validator** — dedicated `safety` hop with ABSTAIN prompt for ungrounded cases.
4. **No checkpointer / no stale tool state** — fresh `invoke()` per case; no MemorySaver leak.

## Parity with Container D

| Dimension | C | D |
|-----------|---|---|
| Prompts | `benchmark/healthcare/prompts.py` (plain text) | `container_d/prompts.py` (JSON-shaped; text-mode API) |
| Tools / KB | `benchmark/healthcare/tools.py`, `kb.py` | Same |
| Cases | `healthcare_workload.py` | Same |
| Model | `InstrumentedGeminiClient` (Gemini 2.5 Flash) | Same |
| Graph framework | LangGraph text/JSON state | LangGraph + Prism envelope per hop (no orphan ingress) |

**Only difference:** D adds `vector_ingress` (embed once) and appends a `PrismEnvelope` per hop; C passes growing text context.

## Where a LangGraph expert might call C weak

1. **No supervisor routing** — fixed linear pipeline per depth, not dynamic ReAct routing. Acceptable for controlled depth sweep; does not test emergent orchestration.
2. **KB is keyword retrieval**, not live pgvector — documented stand-in; both C and D use the same corpus.
3. **Depth-2 path skips retrieve/drug/safety** — by design for shallow sweep; depth 4/6 exercise full tool chain.
4. **No human-in-the-loop** — batch benchmark only.
5. **Single process** — no distributed CHORUS transport (Phase 2 flag in handoff).

## Verification commands

```powershell
# Offline: tools + graph structure (no API)
python -m pytest tests/test_multiagent_pipeline.py -q

# Live dry-run (requires GEMINI_API_KEY)
python -m benchmark.run_multiagent --cases 18 --output-dir benchmark/results/h13_multiagent_dryrun
```

## Audit checklist (H13)

- [x] Retrieve hop calls `retrieve_guidelines` (depth ≥ 4)
- [x] Drug hop calls `check_drug_interactions` when drugs present (depth 6)
- [x] Safety hop can set `abstained=True`
- [x] Writer produces final `response`
- [x] Per-hop metrics recorded (`HopMetric` list)
- [x] Same prompts/tools/cases as D

*Fair baseline C · H13 · competent LangGraph multi-agent · no rigging.*
