# Handoff ProductLanding — ChorusGraph marketing website

**Director:** Amin · **Architect:** Claude · **Website agent:** (assign)  
**Style playbook:** [`c:\code\alex-hormozi.md`](file:///c:/code/alex-hormozi.md) — read **in full** before writing copy  
**Product source of truth:** ChorusGraph repo · **Version:** 1.0.0 · **Date issued:** 2026-07-05

---

## 0. Mission

Build a **marketing-oriented product landing site** for ChorusGraph that converts platform leaders and AI engineers — not a docs mirror. Copy must follow **Alex Hormozi’s Pain → Proof → Plan** framework and the **Value Equation**. Lead with **outcomes and proof**, not feature dumps.

**Deliverables for website agent:**

1. Landing page (hero, pain, proof, plan, value stack, pricing tiers, FAQ, CTA)
2. Optional `/plugins/prismrag` subpage (retrieval plug-in story)
3. Download / docs links to GitHub + pip install
4. Visual system: modern, confident, enterprise-trustworthy (dark + accent; avoid generic “AI purple gradient” cliché unless Director prefers)

**Do not:** fake customer logos, fake testimonials, fake urgency countdowns, or unverified performance claims.

---

## 1. Product facts (verified — use these numbers only)

### One-liner

**ChorusGraph** — native agent runtime with semantic cache, swappable PrismRAG retrieval, auditable memory, and enterprise hardening. One pip install. Four plug-in ports.

### Canonical benchmark (Azure run `20260704_212111`)

| Scenario | LangGraph | ChorusGraph | Headline |
|----------|-----------|-------------|----------|
| Finance single | 87.5% | **100%** | Clean sweep |
| Finance multi | 75% | **87.5%** | +12.5 pp |
| Healthcare single | 72.5% | 72.5% | Tie (honest) |
| Healthcare multi | 57.5% | **87.5%** | **+30 pp win** |

Zero errors. Real Gemini. See `docs/BENCHMARK_RESULTS.md`, `benchmark/results/azure_20260704_212111/`.

### H10 repeat-band (FX, 40% repeat)

- Latency p50: **575 ms (B)** vs **4498 ms (A)** — quote as “~8× lower median latency on repeat FX band” with link to methodology
- Cache hit-rate B: **~41%** (Wilson CI)
- **Always disclose:** sliced metrics; B has product features A lacks (cache, Cortex) — see `benchmark/FAIRNESS_H9.md`

### Engineering proof

- **323 tests** pass without live API keys
- **1.0.0** frozen public API
- Docker / k8s deploy path exists

### PrismRAG plug-in (v1.0)

- Fourth swappable port: `RetrievalBackend`
- Default: zero-dep keyword; upgrade: `pip install "chorusgraph[retrieval]"` + optional license for taxonomy remap
- Implementation guide: [`docs/INSTALL.md`](../docs/INSTALL.md) § PrismRAG

---

## 2. Hormozi playbook — filled templates (Section 8)

*Copy this block into site strategy doc; website agent expands into pages.*

### Avatar (primary)

- **Title:** VP Engineering / Head of AI Platform / Staff ML Engineer
- **Company:** B2B SaaS with shipped LLM feature (support, finance, healthcare copilot, internal tools)
- **Bleeding pain:** $3k–$50k/mo LLM spend + 2–3 eng-months integrating cache/RAG/checkpoint/audit
- **Budget authority:** Often needs CFO/CTO sign-off above $25k/yr

### Dream outcome

- **Statement:** “Cut agent token spend and ship audited, retrieval-grounded agents in weeks — without standing up a separate vector platform team.”
- **Metric:** 30–50% token reduction on repeat intent; healthcare multi-agent +30 pp accuracy vs baseline (our benchmark)
- **Horizon:** First staging proof in **14 days**; production pilot in **30–90 days**

### Value Equation scores (1–10) — fix weakest in copy

| Variable | Score | Copy lever |
|----------|-------|------------|
| Dream Outcome | 9 | Lead with $ + accuracy + audit |
| Perceived Likelihood | 7 | Benchmarks, test count, open methodology — **boost with pilot guarantee** |
| Time Delay | 8 | `pip install` + 60s hello world |
| Effort & Sacrifice | 7 | Plug-in ports, Compose docs — **boost with “golden path in 20 lines”** |

**Weakest lever to fix on site:** Perceived Likelihood → proof section + conditional pilot guarantee

### Grand Slam Offer name

**Free:** “Agent Stack Audit” (30 min)  
**Paid pilot:** “Production Agent Pilot”  
**Recurring:** “ChorusGraph Pro” (PrismRAG + support)  
**Enterprise:** “ChorusGraph Enterprise” (SLA, compliance, air-gap)

### Offer stack (value anchor — adjust dollars with Director)

| Component | Solves obstacle | Anchor |
|-----------|-----------------|--------|
| Core runtime + semantic cache | Integration hell | $50k eng/year |
| 4 swappable ports (incl. PrismRAG) | “Another vector project” | $30k |
| Route Ledger + replay | Audit / compliance | $25k |
| Docker/k8s + health | Ops approval | $15k |
| Benchmark report vs LangGraph | “Won’t work here” | $10k |
| Shadow cache pilot on staging | ROI proof | $8k |
| **Total anchor** | | **~$138k** |
| **Pilot price (suggested)** | | **$8k–$15k** one-time |

### Guarantee (conditional — only if sales can honor)

> On a 14-day staging shadow: if repeat-intent cache hit rate doesn’t exceed your baseline by ≥15 percentage points on agreed traffic, **pilot fee credited** toward implementation.

### Pain → Proof → Plan

**Pain (hero subhead options — pick one):**

- “You’re paying to re-answer the same question — and you still can’t replay why the agent said it.”
- “Your agent stack is six repos duck-taped together. One missing piece blocks production.”

**Proof (3 bullets max above fold):**

1. **+30 pp** healthcare multi-agent vs competent LangGraph baseline (Azure, verified)
2. **323 tests**, no API keys required for CI parity
3. **PrismRAG plug-in** — vector + taxonomy retrieval in ~20 lines, not a benchmark fork

**Plan (3 steps):**

1. **Install** — `pip install "chorusgraph[retrieval]"`
2. **Wire** — `ChorusStack.with_retrieval(PrismRAGRetrievalBackend(...))`
3. **Measure** — Route Ledger + cache hit report on your staging traffic

**CTA (named — never “Learn more”):**

- Primary: **“Book a 30-Min Agent Stack Audit”**
- Secondary: **“Read the Whitepaper”** → `docs/WHITEPAPER.md`
- Tertiary: **“View on GitHub”**

---

## 3. Site map (recommended)

```
/                          Landing (Hormozi structure)
/plugins                   Plug-in architecture overview
/plugins/prismrag          PrismRAG deep page (pip + code sample)
/docs                      Link out to GitHub docs/ (or embedded)
/pricing                   3-tier + enterprise contact
/whitepaper                PDF or long-scroll from WHITEPAPER.md
/benchmarks                Honest results + fairness disclosure
/security                  Enterprise trust (link THREAT_MODEL, STABILITY)
```

---

## 4. Page wireframe — landing `/`

### Hero

- **Headline (outcome):** “Ship production agents without the integration tax.”
- **Subhead (pain):** Token burn + audit gap + six-month glue projects
- **Proof strip:** +30 pp HC · 100% FC1 · 323 tests · pip install
- **CTA:** Book Agent Stack Audit · [GitHub] · [Whitepaper]

### Section: Pain (quantified)

Use avatar language. Example blocks:

- LLM line item growing faster than revenue
- Compliance asking for replay; you have logs, not decisions
- Pinecone + LangGraph + Redis + custom rerank = three teams

### Section: Proof

- Benchmark table (§1 above) — **include HL1 tie honestly**
- Link to fairness doc
- Optional: animated latency comparison (575 vs 4498 ms) with footnote “H10 repeat band, sliced”

### Section: Plan — “Three steps to staging”

1. Install (`docs/INSTALL.md` code block)
2. Stack + PrismRAG (short code sample from below)
3. Deploy health check (`curl /health`)

### Section: Value stack — “What you get”

Four ports diagram + enterprise modules (E1–E9 one-liners)

### Section: PrismRAG plug-in callout

```python
pip install "chorusgraph[retrieval]"

stack = (
    ChorusStack.defaults(tenant_id="acme")
    .with_retrieval(PrismRAGRetrievalBackend(
        embedder=PrismlangOnnxEmbedder(),
        mapping=YOUR_MAPPING,
    ))
)
stack.resolve_retrieval().index(YOUR_CORPUS)
retrieve_node = stack.to_retrieve_handler(topic="policy", top_k=6)
```

Link: **Full implementation guide** → `docs/INSTALL.md`

### Section: Pricing (3 tiers)

| Tier | For | Includes | Price |
|------|-----|----------|-------|
| **Open Source** | Developers | pip package, keyword retrieval, docs | Free |
| **Pro** | Teams | PrismRAG license, email support, updates | TBD/mo |
| **Enterprise** | Regulated | SLA, pilot, Postgres roadmap, security review | Contact |

### Section: FAQ

- “Is this LangGraph?” → **No** for product; LangGraph = baselines only (`docs/TERMINOLOGY.md`)
- “Do I need a PrismRAG license?” → Vector works without; remap needs key
- “HIPAA / SOC2?” → Controls built; external audit Phase 2 — honest
- “Postgres?” → SQLite 1.0; Postgres Phase 2

### Footer

Insight IT Solutions · Apache-2.0 · GitHub · Whitepaper · Privacy

---

## 5. Visual / tone guidelines

- **Tone:** Confident, direct, numbers-first — Hormozi style without bro-marketing cringe
- **Avoid:** “Revolutionary AI”, patent walls, unqualified “10× everything”
- **Include:** Fairness disclosures, Phase 2 honesty (builds trust with technical buyers)
- **Typography:** Strong headline sans; monospace for code blocks
- **Social proof (when available):** InsightitsAIAgent dogfood reference — no fake logos

---

## 6. Assets to pull from repo

| Asset | Path |
|-------|------|
| Whitepaper (long form) | [`docs/WHITEPAPER.md`](../docs/WHITEPAPER.md) |
| Install + PrismRAG guide | [`docs/INSTALL.md`](../docs/INSTALL.md) |
| Plug-in reference | [`docs/PLUGINS.md`](../docs/PLUGINS.md) |
| Enterprise readiness | [`docs/ENTERPRISE_READINESS.md`](../docs/ENTERPRISE_READINESS.md) |
| Benchmark methodology | [`docs/BENCHMARK.md`](../docs/BENCHMARK.md) |
| Fairness | [`benchmark/FAIRNESS_H9.md`](../benchmark/FAIRNESS_H9.md) |
| API stability | [`docs/STABILITY.md`](../docs/STABILITY.md) |
| Hormozi playbook | [`c:\code\alex-hormozi.md`](file:///c:/code/alex-hormozi.md) |
| Architecture diagram source | `docs/COMPOSE.md`, whitepaper §3 |

---

## 7. Website agent checklist (exit criteria)

- [ ] Read `alex-hormozi.md` Sections 1–9 before writing
- [ ] Hero uses **Pain → Proof → Plan**; CTA is named
- [ ] All numbers match §1 (no invented stats)
- [ ] HL1 tie disclosed; H10 metrics labeled “sliced”
- [ ] PrismRAG page includes pip install + 20-line sample + link to `INSTALL.md`
- [ ] Pricing uses 3-tier + enterprise; no fake scarcity
- [ ] Whitepaper linked or rendered
- [ ] Mobile-responsive; code blocks readable
- [ ] Lighthouse accessibility ≥ 90 (target)

---

## 8. 30-day launch (suggested)

| Week | Focus |
|------|-------|
| 1 | Landing + `/plugins/prismrag` + GitHub/docs links |
| 2 | Whitepaper page + benchmark honesty page |
| 3 | Pricing + audit booking flow (Calendly or form) |
| 4 | Pro tier waitlist + first case study when available |

---

## 9. Out of scope for website agent

- PyPI publish (separate release task)
- Fake testimonials / logos
- Committing to Postgres delivery dates beyond “Phase 2”
- Modifying ChorusGraph engine code

---

## 10. Return format (`handoffbackProductLanding.md`)

- Live URL or preview link
- Screenshot of hero + proof section
- Hormozi template confirmation (avatar, guarantee, CTA name)
- List of any copy claims that needed Director approval
- Lighthouse / a11y scores

---

*ProductLanding · website handoff · Hormozi-style GTM · PrismRAG as hero plug-in · honest benchmarks · 2026-07-05.*
