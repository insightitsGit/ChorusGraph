# Loop token-burn findings (2026-07-17)

Response to `docs/HANDOFF-LOOP-TOKEN-BURN-PAIN-2026-07-17.md` (TokenShield inbound).  
**Do not** integrate or endorse TokenShield.

**Shipped follow-up:** [`ADR-007-react-repeated-action-default.md`](ADR-007-react-repeated-action-default.md) — `stop_on_repeated_action=True` by default.

---

## 1. REAL_PAIN: **partial**

**Industry class:** yes — stuck ReAct / self-heal loops that emit *unique* prompt or tool-arg variants will miss semantic L1 cache and spend provider tokens.

**For ChorusGraph users today:** only *partially* painful, because agent patterns are **hard-capped** by step/tool budgets. You do **not** get unbounded “minutes of wallet burn” from a single `Agent.run()` under defaults — you get a bounded burst (~`max_steps` LLM calls). Residual risk is real when operators raise budgets, compose many agent nodes, or call LLMs outside `PlanPolicy`.

### Evidence

| Source | Result |
|--------|--------|
| GitHub issues / search (`runaway`, `wallet`, `token burn`, thrash) | **No** user reports found |
| Code defaults (post ADR-007) | `PlanPolicy(max_steps=8)`; `ReActOpts(max_tool_calls=6, stop_on_repeated_action=True)` |
| Probe `scripts/_probe_loop_token_burn.py` | See table below |
| PrismCache L1 | By design skips **duplicate/near-dup user queries**, not unique in-loop prompts |

**Probe (fixture LLM, finance tool registry):**

| Case | Config | Outcome |
|------|--------|---------|
| A | Identical tool+args, `stop_on_repeated_action=False` | `finish=max_steps`, **6** LLM calls |
| B | Same, `stop_on_repeated_action=True` (**now default**) | `finish=repeated_action`, **2** LLM / **1** tool |
| C | Alternating EUR/GBP args, stop on | `finish=repeated_action` after cycle repeats EUR (**3** LLM) |
| C2 | **Never-repeat** unique `principal=1000+n` | `finish=max_steps`, **8** LLM — **repeated_action cannot fire** |
| D | Default `token_budget=8000`, short JSON replies | Still `finish=max_steps` — **token_budget does not bind** |

TokenShield’s “unique rapid-fire variants” maps to **C2**, not C. Exact repeated-action stop helps identical thrash; unique args each hop still burn up to `max_steps` / `max_tool_calls`.

---

## 2. ALREADY_COVERED

| Mechanism | Where | Stops unique-loop burn? |
|-----------|-------|-------------------------|
| `PlanPolicy.max_steps` (default **8**) | `policy.py`, `loop.py` | **Yes — hard cap** on reason↔act cycles |
| `ReActOpts.max_tool_calls` (default **6**) | `react_strategy.py` | **Yes** on tool fan-out |
| `stop_on_repeated_action` (default **True**, ADR-007) | `react_strategy.py` | **Only exact** `(tool, json.dumps(args))` replay |
| Reflection pass caps | `max_revisions` ∩ `max_reflection_passes` | **Yes** — bounded revise loop |
| Scheduler `recursion_limit` (default **25**) | `scheduler.py` / `Graph.compile` | Caps **graph super-steps**, not nested LLM thrash *inside* one node |
| PrismCache L1 | cache gate | **No** for unique in-loop prompts (correct product scope) |
| Route Ledger | ledger | Observability — **no** spend / loop circuit breaker |

---

## 3. REMAINING GAP

1. **No fuzzy / windowed / prompt-hash breaker** — unique args each hop (C2) still burn the full step budget.
2. **`token_budget` is crude** — `len(raw) // 4` on reason JSON only.
3. **`on_exhaust` is API-only** — not consulted in `loop.py` (docs now say deferred).
4. **`cost_budget`** not on `PlanPolicy`.
5. No ledger `loop_suspected` / `budget_exhausted` events yet.

---

## 4. RECOMMENDATION STATUS

| Item | Status |
|------|--------|
| Default `stop_on_repeated_action=True` | **Shipped** ([ADR-007](ADR-007-react-repeated-action-default.md)) |
| Docs honesty (L1 ≠ unique loops; `on_exhaust` / token_budget caveats) | **Shipped** (`DEVELOPER_GUIDE.md`) |
| Fuzzy signature breaker / real token accounting | Optional later |
| TokenShield / network proxy | **No** |

### Related: L1 single-flight (separate)

Concurrent same-key stampede → [`ADR-006-l1-single-flight.md`](ADR-006-l1-single-flight.md) (opt-in, default off).

---

## 5. GTM_SAFE_LINE

> PrismCache L1 cuts **repeat** LLM tax on similar user queries; agent loops are capped by `PlanPolicy.max_steps` / `max_tool_calls`, and ReAct stops on **exact** repeated tool+args by default — not by L1, and not by an unbounded network circuit breaker. Opt out of the repeated-action stop when intentional retries are required.

---

## 6. Decision for Amin / Marketing

| Question | Answer |
|----------|--------|
| Is TokenShield’s failure mode real? | **Yes** as an industry class. |
| Is ChorusGraph “broken” without them? | **No** — L1 scope is correct; agents hard-cap steps + default thrash stop. |
| Residual gap worth owning further? | Optional only (fuzzy breaker / token accounting). |
| Partner / ship their binary? | **No.** |

Reproduce evidence: `python scripts/_probe_loop_token_burn.py`

---

## README follow-up (no release)

**2026-07-17 Amin:** README PrismGuard companion still pins `0.1.4` — fix to `0.1.7` on the **next** ChorusGraph cut. Do not ship a patch release only for README.
