# Handoff ProductLanding — ChorusGraph marketing website

**Director:** Amin · **Architect:** Claude · **Website agent:** (assign)  
**Style playbook:** [`c:\code\alex-hormozi.md`](file:///c:/code/alex-hormozi.md) — read **in full** before writing copy  
**Product source of truth:** ChorusGraph repo · **Version:** 1.0.1 · **Date issued:** 2026-07-05

---

## 0. Mission

Build a **marketing-oriented product landing site** for ChorusGraph that converts platform leaders and AI engineers — not a docs mirror. Copy must follow **Alex Hormozi’s Pain → Proof → Plan** framework and the **Value Equation**. Lead with **outcomes and proof**, not feature dumps.

**Deliverables for website agent:**

1. Landing page (hero, pain, proof, plan, value stack, pricing tiers, FAQ, CTA)
2. Optional `/plugins/prismrag` subpage (retrieval plug-in story)
3. Download / docs links to GitHub + pip install
4. Visual system: modern, confident, enterprise-trustworthy (dark + accent; avoid generic “AI purple gradient” cliché unless Director prefers)
5. **60-second hero/ad video** (script in §2.5 below) — embed at the top of the landing page and reuse
   as a standalone social/ad asset (LinkedIn, X, YouTube pre-roll)

**Do not:** fake customer logos, fake testimonials, fake urgency countdowns, or unverified performance claims.

**Hard release gate — verify before ANY page goes live with a `pip install` snippet:**
```powershell
python -m venv clean_test_env
clean_test_env\Scripts\pip install chorusgraph
clean_test_env\Scripts\python -c "import chorusgraph; from chorusgraph import Graph, ChorusStack; print(chorusgraph.__version__)"
```
**Status (2026-07-05):** Fixed in v1.0.1 — core deps include `prismlib-plus` and `prismresonance`. Re-run this exact command after any dependency change before publishing the hero install snippet or "60s hello world" claim.

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
**Enterprise:** “ChorusGraph Enterprise” (SLA, compliance, Postgres HA)
  — **do NOT say "air-gap" anywhere on the site.** Verified 2026-07-05: PrismRAG's license check calls
  home to a remote server with only a 7-day offline grace period — true zero-connectivity air-gap is not
  deliverable until the offline license mechanism ships (see `PrismRagLib/handoffs/handoff1_licensing.md`).
  Re-check this note before removing it.

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

**Alternate plan (strong, add as a callout box):** "Or skip the manual steps — paste our AI IDE prompt
into Cursor/Claude Code/Copilot and it installs + wires ChorusGraph into your project for you."
Link to `docs/AI_IDE_PROMPTS.md` (README already surfaces this). This is a genuinely differentiated
proof point for the weakest lever (Perceived Likelihood / Effort) — a visitor can literally watch their
own AI agent do the integration live, which is more convincing than any code sample on the page.

**CTA (named — never “Learn more”):**

- Primary: **“Book a 30-Min Agent Stack Audit”**
- Secondary: **“Read the Whitepaper”** → `docs/WHITEPAPER.md`
- Tertiary: **“View on GitHub”**

---

## 2.5 60-second hero/ad video (script — produce, do not invent new claims)

**Format decision (deliberate):** no voiceover, caption-driven, real screen footage — LinkedIn/X autoplay
muted by default, so a video that only works with sound loses most viewers in the first second. Bold
captions over *real* terminal output reads as proof to this audience; a narrator reads as marketing.

**Cheap to produce:** the two terminal segments are a real screen recording (OBS Studio or Loom, free),
the stat cards reuse the existing flyer's dark-background/teal-accent branding, editing is just cuts +
text overlays (CapCut or DaVinci Resolve, free) — no animation, no actors.

| Time | Visual | On-screen text |
|---|---|---|
| 0:00–0:05 | Black screen, blinking cursor | "Every agent stack pays the same tax." |
| 0:05–0:10 | Fast, slightly chaotic list flashing | "LangGraph + Redis + Pinecone + checkpoints + audit logs = six repos, glued together" |
| 0:10–0:14 | Hard cut to a clean terminal | "Or: one command." |
| 0:14–0:24 | **Real recording**: `pip install chorusgraph` actually running (sped up if needed) | (minimal text, let it run) |
| 0:24–0:32 | **Real recording**: the hello-world snippet, real output appearing | `{'reply': 'Hello, ChorusGraph'}` — genuinely printed, not mocked |
| 0:32–0:40 | Bold stat cards, dark bg, teal accent (reuse flyer look) | "+30pp healthcare multi-agent vs. LangGraph" → "100% vs 87.5% finance success" |
| 0:40–0:46 | Same stat-card style | "323 tests. Zero API keys to verify. Zero fake stats." |
| 0:46–0:53 | Quick 3-line code cut: swapping in `PrismRAGRetrievalBackend` | "Swap ports, don't fork the engine." |
| 0:53–0:58 | End card, same flyer branding | `pip install chorusgraph` · `github.com/insightitsGit/ChorusGraph` |
| 0:58–1:00 | Final hold | "Real Gemini calls. Real benchmarks. Zero fake stats." |

**Every number in this script is already verified against raw logs elsewhere in this repo — do not add
a new claim to the video that isn't in §1.** If a shorter 15-second cutdown is needed for platforms
where 60s is too long, cut straight from 0:00–0:10 (pain) to 0:32–0:40 (the two headline stats) to
0:53–1:00 (CTA) — skip the terminal demo in the cutdown, it needs the full minute to land.

---

## 3. Site map (recommended)

```
/                          Landing (Hormozi structure)
/plugins                   Plug-in architecture overview
/plugins/prismrag          PrismRAG deep page (pip + code sample)
/docs                      Link out to GitHub docs/ (or embedded)
/pricing                   3-tier + enterprise contact
/whitepaper                PDF or long-scroll from WHITEPAPER.md
/benchmarks                Honest results + fairness disclosure — include the exact
                           `python -m benchmark.run_scenarios ...` repro command, not just the table.
                           A reader who can reproduce the number themselves is worth ten who just read it.
/security                  Enterprise trust (link THREAT_MODEL, STABILITY)
/blog (optional, strong)   The engineering honesty story is a real distribution asset: "our first
                           benchmark said we won 82–27 — it was lying, here's how we caught it,"
                           the H21 depth-6 cache-quality investigation, the temperature-noise finding.
                           This kind of transparent post-mortem is rare in vendor content and is
                           exactly what earns HN/technical-audience trust — don't leave it unpublished.
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
| **NotebookLM story source** (for the audio/video overview) | [`docs/NOTEBOOKLM_STORY.md`](../docs/NOTEBOOKLM_STORY.md) — feed this into NotebookLM to generate the hero video/audio; every fact in it is source-cited at the bottom, don't let the generated output drift from it |

---

## 7. Website agent checklist (exit criteria)

- [ ] **`pip install chorusgraph` verified in a throwaway clean venv THIS SAME DAY** (see hard gate in §0) —
      not assumed from a prior pass. Re-check if the release engineer says it was "just fixed."
- [ ] Read `alex-hormozi.md` Sections 1–9 before writing — **if the assigned agent cannot resolve
      `c:\code\alex-hormozi.md`** (local-machine path, not in this repo), request the Director copy the
      needed excerpt into `docs/` first rather than writing copy blind to the playbook
- [ ] Hero uses **Pain → Proof → Plan**; CTA is named
- [ ] All numbers match §1 (no invented stats)
- [ ] HL1 tie disclosed; H10 metrics labeled “sliced”
- [ ] PrismRAG page includes pip install + 20-line sample + link to `INSTALL.md` — **sample actually run**
      against a fresh install, output pasted into the return doc, not copied from the whitepaper unverified
- [ ] Pricing uses 3-tier + enterprise; no fake scarcity
- [ ] Whitepaper linked or rendered; **also export a clean PDF** for the classic B2B email-gated download
      (many enterprise buyers expect a PDF, not just a scrolling page)
- [ ] Mobile-responsive; code blocks readable
- [ ] Lighthouse accessibility ≥ 90 (target)
- [ ] CTA buttons carry basic UTM/analytics tags so click-through on "Book Agent Stack Audit" is
      measurable from week 1 — the earlier marketing-metrics discussion flagged inbound-per-week and
      activation as the two leading indicators worth tracking from day one, not added later
- [ ] Nothing from `docs/THREAT_MODEL.md` beyond the summary level is exposed verbatim on `/security` —
      link a one-paragraph public summary, not the internal attack-surface enumeration

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
