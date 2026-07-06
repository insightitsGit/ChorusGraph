# The ChorusGraph Story — source narrative for NotebookLM

**Purpose:** feed this document into Google NotebookLM to generate an audio/video overview for the
landing page and other channels. Structured deliberately on the Hormozi framework
(`c:\code\alex-hormozi.md`): Pain stated in dollar terms → Proof led by the measured savings number →
Plan in three steps → a named call to action, never "learn more." Every fact, number, and claim below is
verified against raw logs, real code, or a real clean-room test elsewhere in this repository — nothing
here is invented for narrative effect, including the savings numbers. If NotebookLM's output drifts from
a specific number, correct it against this source, not the other way around.

---

## Chapter 1 — The pain, in dollars

If your team runs LLM agents in production, here's the uncomfortable number nobody puts in their pitch
deck: a meaningful share of your monthly model bill is spent re-answering questions you've already
answered. Every repeated or near-duplicate question your agent gets, it re-runs the full reasoning
chain from scratch — the same retrieval call, the same multi-step analysis, the same tokens, billed
again, because nothing in a standard LangGraph stack remembers that it already did this work five
minutes ago.

That's not a guess. Measured directly, on a fair, apples-to-apples benchmark against a competent
LangGraph baseline — same model, same tools, same prompts, only the framework changed — pulled directly
from the canonical run's own comparison data (`benchmark/results/mvp_scenarios/20260704_212111/comparison.json`,
re-verified before this document was finalized):

- **Finance, single-agent workload:** 72% fewer LLM calls per task. Cost per task down 70%.
- **Finance, multi-agent workload:** 60% fewer LLM calls per task. Cost per task down 58%.
- **Healthcare, single-agent workload:** 35% fewer LLM calls per task. Cost per task down 14%.
- **Healthcare, multi-agent workload:** 10% fewer LLM calls per task; cost per task is essentially flat
  (not a savings story here — see Chapter 1a).

**Overall (equal-weight across all four scenarios, same canonical run):** ~44% fewer LLM calls per task
and ~35% lower modeled Gemini cost vs LangGraph. Finance workloads average ~66% fewer calls and ~64%
lower cost; healthcare averages ~22% fewer calls and ~6% lower cost — because healthcare deliberately
re-runs clinical judgment even on cache hits (Chapter 1a).

The cost savings are real and substantial in finance. In healthcare, they're modest by design, and
Chapter 1a explains exactly why — the honest reason is more interesting than a bigger number would be.
Those percentages come directly from the benchmark's own cost calculation, computed on real Gemini
pricing, not estimated. The honest caveat, stated plainly rather than hidden: the exact dollar amount
this means for *your* bill depends on your own traffic volume and how often your users ask similar
questions — which is exactly why the right first step isn't a sales pitch, it's running the same
measurement on your own traffic. More on that in Chapter 6.

## Chapter 1a — Why healthcare doesn't save much money (and why that's the right design, not a shortfall)

Finance and healthcare hit the cache very differently on purpose. In finance, a repeated question
gets its whole answer replayed — that's where the 60-70% cost cuts above come from. In healthcare, a
cache hit only ever reuses *facts* — retrieved guidelines, drug-interaction lookups. The actual
clinical judgment (the reasoning that decides what to recommend) always re-runs fresh, every single
time, even on a "hit." That's a deliberate safety rule: replaying a cached medical judgment without
re-checking it against the specific patient in front of you would be unsafe, so the system refuses to
do it. The consequence is honest and worth saying plainly: healthcare's cache saves you very little
money, because it was never designed to cut corners on the part of the job that actually matters.
What it *does* buy you, measured on the same benchmark: a 30-percentage-point jump in task success
(Chapter 4) — the win in this domain is accuracy, not cost, and that's the correct tradeoff for
anything regulated or safety-critical.

Those percentages come directly from the benchmark's own cost calculation, computed on real Gemini
pricing, not estimated. The honest caveat, stated plainly rather than hidden: the exact dollar amount
this means for *your* bill depends on your own traffic volume and how often your users ask similar
questions — which is exactly why the right first step isn't a sales pitch, it's running the same
measurement on your own traffic. More on that in a moment.

## Chapter 2 — The dream outcome

Cut your agent's LLM spend — up to 70% in finance-shaped, repeat-question-heavy workloads — without
hiring a platform team, standing up Redis, or running a vector-database migration project. In
judgment-heavy, regulated domains like healthcare, the dream outcome looks different and is stated as
such, not inflated to match: materially higher task accuracy (Chapter 1a, Chapter 4), with cost savings
that are honestly modest. Either way: first proof of savings, on your own traffic, in 14 days. That's the
target, and it's the same target the benchmark numbers above were measured against.

## Chapter 3 — Why trust the number (the proof behind the proof)

Here's the part most vendors don't tell you: building this meant catching our own mistakes along the
way, and keeping the discipline of verifying every claim against raw evidence rather than trusting a
summary — including our own.

Early on, an internal benchmark claimed a huge win — the summary numbers looked great. Checking the raw
task logs instead of the summary revealed the baseline had a real bug: it wasn't calling its tools at
all, so the comparison was worthless. That got fixed, and the baseline was rebuilt to be genuinely
competent before any real comparison ran again.

Later, a multi-agent test showed the new engine performing *worse* than a single agent — which made no
sense on its face. Digging into the actual execution trace found the real cause: a caching shortcut was
skipping a reasoning step it shouldn't have skipped. Once fixed and re-measured properly, the real result
emerged — a genuine, verified improvement, not a shortcut.

Even the measurement tooling itself got scrutinized: an early comparison run showed one side losing
ground between two runs with zero code changes — the LLM's sampling temperature wasn't pinned, so noise
was being mistaken for a real signal. Pinning temperature and re-running is what finally produced
trustworthy numbers.

A separate mistake almost made it into marketing: an earlier healthcare multi-agent run showed ChorusGraph
at **1.02 LLM calls per task** versus LangGraph's 3.85 — a spectacular cost win. Raw task logs showed
why that number was invalid: cache hits skipped clinical judgment hops and replayed earlier *failures*,
and task success **fell** to 45%. After Bug-1 fix (`663edf7`), the canonical run reports **3.48** LLM
calls per task — modest savings — but task success jumps to **87.5%**. We quote the post-fix numbers only;
see `handoffs/handoffbackaudit.md` for the full invalid-vs-canonical comparison.

This is the whole reason the savings percentages in Chapter 1 are stated as percentages measured on a
controlled benchmark, not as a blanket "you'll save $X/month" claim extrapolated from someone else's
traffic pattern — that would be exactly the kind of number this project's own discipline exists to catch.

## Chapter 4 — The full proof (accuracy, not just cost)

The canonical benchmark — real Gemini calls, 40 tasks per scenario, verified line by line against raw
output logs, run ID `20260704_212111` — also measured task success, not just cost:

- **Finance, single agent:** 87.5% → **100%**, a clean sweep.
- **Finance, multi-agent:** 75% → **87.5%**.
- **Healthcare, single agent:** 72.5% → 72.5% — an honest tie, disclosed as a tie, not spun as a win.
- **Healthcare, multi-agent — the standout result:** 57.5% → **87.5%**, a 30-percentage-point
  improvement, achieved with *fewer* LLM calls and a *lower* abstain rate than the baseline. Zero errors
  across the entire run.

The pattern across every scenario: accuracy is equal-or-higher, never traded away for a cheaper answer —
cost comes down substantially where the cache can safely reuse a whole answer (finance), and stays flat
where safety rules say it shouldn't (healthcare, Chapter 1a). Underneath it: **342 tests pass without a
single API key** — a deterministic test tier records
real Gemini and tool responses once, then replays them, so anyone can verify the engineering quality
without needing credentials or spending a cent.

## Chapter 5 — Proven again, in a real production system

A real production agent — a live company website chatbot, already running LangGraph — was migrated to
this engine as a genuine test, not a staged demo. Fifteen graph nodes, conditional routing, a retry
loop, real production traffic patterns. The migration succeeded: all 46 of the agent's existing tests
passed against the new engine. The process also found a real bug in the compatibility layer — surfaced
only because a real, complex production graph exercised a code path a synthetic test never would have.
It's been fixed and shipped, because the standard here is that real-world use, including the parts that
go wrong, gets fixed and disclosed, not hidden.

## Chapter 6 — The offer stack

**Free, permanently:** `pip install chorusgraph` — the full native engine, semantic cache, and a
keyword-based retrieval layer, Apache-2.0. Not a trial. This is where the cost-reduction numbers in
Chapter 1 already start applying, at zero cost.

**Cold audit (free, no API key):** `chorusgraph-audit --log your_queries.jsonl` — upload your historical
query log (CSV or JSONL) and get a **simulated** repeat/near-duplicate rate using the same semantic gate
the product uses in production. Optional token columns produce a modeled cost estimate; without them, no
dollar line is shown. This is the self-serve step before any sales call — honest language, no LLM calls,
mandatory disclaimer that the Production Agent Pilot measures *real* traffic over 14 days.

**Production Agent Pilot ($8k–15k, one-time):** a 14-day shadow-cache proof on your own staging traffic
— your real hit-rate and token-savings report (`chorusgraph-audit --ledger <run_id>` on the Route Ledger),
one production graph wired, a benchmark-style readout against your current stack. The guarantee: if
repeat-intent cache hit rate doesn't clear your baseline by at least 15 percentage points in 14 days,
the pilot fee is credited toward implementation. This is the step that turns Chapter 1's measured
percentages into *your* actual dollar number. Live ledger reports today include measured cache hits and
latency; dollar totals from ledger data await an optional token-field schema addition (disclosed, not
faked).

**Pro ($149–500/month per production environment):** production-grade vector retrieval with
taxonomy-aware accuracy, plus support.

**Enterprise ($25k–100k+/year):** everything above, locked in production, with an SLA, multi-tenant
security isolation, and durable persistence for regulated, high-availability deployments.

## Chapter 7 — What's still being built (said plainly)

Not everything is finished, and this document says so on purpose. A fully offline, zero-connectivity
license validation path is in progress, not shipped yet. When it ships, this document gets updated —
the goal is that nothing said in public ever gets ahead of what's actually true in the code.

## Chapter 8 — The plan

Three steps. Nothing vague.

1. **Install** — `pip install chorusgraph`. Working agent graph in the time it takes to read this
   sentence.
2. **Cold audit** — `chorusgraph-audit --log your_queries.csv` (or JSONL). No API key. Simulated
   hit rate on your own query history using the real semantic gate — not a demo, not a sales pitch.
   Benchmark portfolio for context: ~44% fewer LLM calls and ~35% lower modeled Gemini cost across our
   four canonical scenarios (finance ~64% cost down; healthcare cost modest by design).
3. **Pilot** — book the Production Agent Pilot for 14 days on staging traffic, or run benchmarks with
   your own Gemini key. `chorusgraph-audit --ledger <run_id>` reports measured cache hits and latency
   from the Route Ledger.

**Book a 30-Minute Agent Stack Audit** — that's the next step, not "learn more" and not "contact us."
Bring a query log; leave with a simulated hit-rate number and an honest read on whether a pilot is
worth it for your traffic shape.

---

*Source facts: `benchmark/results/mvp_scenarios/20260704_212111/comparison.json` (canonical —
post–HC2 Bug-1 fix; do **not** use pre-fix run `20260703_042206` for HC2 cost claims), Azure mirror
`benchmark/results/azure_20260704_212111/`, Gemini pricing in `benchmark/shared/instrumented_gemini.py`,
audit tool `chorusgraph/audit/` and `handoffs/handoffbackaudit.md`, `docs/BENCHMARK.md`,
`docs/WHITEPAPER.md`, `handoffs/handoffBug1.md`, `handoffs/handoffbackBug1.md`,
`docs/ENTERPRISE_READINESS.md`, `docs/STABILITY.md`, `handoffs/handoffProductLanding.md` (offer stack,
guarantee, pricing). Do not add a claim to any generated audio/video that isn't traceable to one of
these sources — especially do not let a generated video assert a blanket dollar-per-month savings figure;
the percentage reductions in Chapter 1 are measured benchmark comparisons, the portfolio overall is
~44% LLM / ~35% modeled cost, and the dollar figure for a specific prospect is what the cold audit
(simulated) and Production Agent Pilot (measured) exist to compute.*
