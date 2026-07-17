# Handoff — Agent loop token-burn pain (investigate + possible fix)

**Repo:** ChorusGraph (`c:\code\ChorusGraph`)  
**Date:** 2026-07-17  
**From:** Marketing / Amin (inbound email after HN visibility)  
**For:** ChorusGraph product/engineering agent  
**Priority:** Investigate whether this is a **real user pain** we should own — then design a fix **only if** gap is real and in-scope.

---

## Inbound claim (TokenShield email → Amin)

Sender pitched **TokenShield**: a local proxy / circuit breaker for runaway background agent loops.

Their thesis (paraphrased):

1. **PrismCache (L1 semantic cache)** is good at skipping **duplicate / near-duplicate** user queries.  
2. **Complex loops** (ReAct, Reflection, self-heal) often emit **unique, rapid-fire prompt variants**.  
3. Semantic cache **does not trip** on those → **API wallet burn** in minutes.  
4. Their fix: **payload-hash / signature pattern** at the **network boundary** (e.g. same pattern 3+ times in 60s → circuit break + mock stream). Zero app code change via `BASE_URL` proxy.

**Marketing verdict already given to Amin:**

- Failure mode is a **real industry class of problem**.  
- It is **not** evidence that ChorusGraph/PrismCache is “broken” — L1 is marketed for **repeat LLM tax**, not “all runaway unique loops.”  
- **Do not** integrate or run their unsolicited alpha binary.  
- Question for this agent: **Do we already cover this? Is the residual gap painful enough to fix in-product?**

---

## Your mission

### 1) Is it a real pain for *our* users?

Answer with evidence, not vibes:

| Check | How |
|-------|-----|
| Do ReAct / Reflection / `run_agent_loop` paths generate unique payloads per hop when stuck? | Trace real or fixture loops; log prompt hashes |
| Have benches / PH / GH issues / support mentioned wallet burn / runaway loops? | Search issues, Discussions, PH replies, internal notes |
| Do defaults fail open (unlimited LLM calls) in common recipes? | Audit examples + docs defaults |
| Would AppSec/platform buyers pay for / require this? | Note only — no fake personas |

**Output:** `REAL_PAIN: yes | partial | no` + short evidence bullets.

### 2) What do we already have?

Inventory (start here — code already hints these exist):

| Mechanism | Where to look | Does it stop unique-loop burn? |
|-----------|---------------|--------------------------------|
| `recursion_limit` (scheduler) | `chorusgraph/core/scheduler.py` | Caps super-steps — yes for graph cycles |
| `PlanPolicy(max_steps, token_budget, on_exhaust=…)` | `docs/DEVELOPER_GUIDE.md`, `docs/API_1_0.md`, agents | Caps agent pattern steps/tokens |
| Repeated-action stop | `tests/test_agent.py` → `test_stop_on_repeated_action_breaks_loop` | Similar to their hash idea? Confirm semantics |
| PrismCache L1 | cache gate / semantic routing | **No** for unique variants (by design) |
| Route Ledger | ledger / audit | Observability — does it alert/budget? |

**Output:** table of **shipped vs gap** vs TokenShield’s “hash 3×/60s at network edge.”

### 3) If gap is real — what should *we* build (native)?

Prefer **in-runtime** controls over “recommend a random proxy binary.”

Candidate directions (evaluate, don’t implement all):

1. **Stronger defaults** — safe `max_steps` / `token_budget` on ReAct/Reflection examples and docs.  
2. **Payload / tool-call signature breaker** — if action+args or prompt fingerprint repeats N times in window → stop (may already exist as repeated-action stop — extend if weak).  
3. **LLM call budget + ledger alarm** — hard stop + Route Ledger event `budget_exhausted` / `loop_suspected`.  
4. **Plugin port** — optional “egress policy” hook (HTTP/LLM provider wrapper) for enterprise hardening — **not** bundling third-party closed binaries.  
5. **Doc honesty** — GTM/FAQ: “L1 ≠ runaway unique loops; use PlanPolicy / …”.

**Out of scope unless Amin says otherwise:**

- Shipping or endorsing TokenShield  
- Running unsolicited binaries  
- Claiming we “fix token burn for all agents” without proof  

### 4) Deliverables back to Amin / Marketing

Write a short reply file (create under `docs/`):

`docs/LOOP-TOKEN-BURN-FINDINGS.md` with:

1. `REAL_PAIN:` yes/partial/no + evidence  
2. `ALREADY_COVERED:` list  
3. `GAP:` list  
4. `RECOMMENDATION:` ignore | docs-only | small fix | larger feature (with rough size)  
5. `GTM_SAFE_LINE:` one honest sentence Marketing can use (or “none yet”)  
6. Optional: issue titles / ADR stub if you recommend a feature  

---

## Context links

- Marketing inbound note: `c:\code\Marketing\kb\outreach\HANDOFF-SITE-LI-OSS-ALIGN-2026-07-17.md` (broader session; this loop topic is separate)  
- Product GTM: `c:\code\Marketing\kb\CHORUSGRAPH_PRODUCT.md` — L1 = repeat LLM calls  
- Interactive demo: https://insightitsgit.github.io/ChorusGraph/demo.html  
- Design: `docs/ENGINE_DESIGN_v0.1.md` (cycles / ReAct loops) · `docs/DEVELOPER_GUIDE.md` (`PlanPolicy`)

---

## Suggested first commands for the agent

```text
1. Read docs/DEVELOPER_GUIDE.md (PlanPolicy, react/reflection)
2. Read tests/test_agent.py (repeated-action stop)
3. Grep: PlanPolicy, recursion_limit, repeated_action, token_budget, max_steps
4. Run or extend a fixture that forces unique self-heal prompts — measure whether budgets stop spend
5. Write docs/LOOP-TOKEN-BURN-FINDINGS.md
```

---

## Success = clear decision

Amin needs: **Is this a real pain we should fix in ChorusGraph, and what’s the smallest honest fix?**  
Not: a partnership with TokenShield.
