# The Handoff Loop — how we build (a reusable technique)

A human-directed, spec-driven, multi-agent development loop. It's how ChorusGraph got built across H1–H8,
and it's reusable on any project. Not magic — just disciplined roles + written contracts + verification.

## Roles

| Role | Who | Owns |
|------|-----|------|
| **Director** | Amin | Goals, decisions, resources/access, priorities. Says what and why; approves scope. |
| **Architect** | Claude | Specs (handoffs), design doc, reviews, scope calibration. Turns intent into bounded, testable work; verifies returns. |
| **Engineer** | Cursor | Implementation. Turns a handoff into real, tested code; returns an honest report. |

## The loop

```
Director sets a goal
   → Architect writes handoffN.md  (a contract: scope, out-of-scope, acceptance)
      → Engineer implements, writes handoffbackN.md  (real results + honest disclosures)
         → Architect reviews AGAINST THE REAL CODE (reads it, runs the tests)
            → Architect writes handoffN+1.md
   (repeat)
```

One handoff = **one bounded increment.** The design doc is the **single source of truth**; handoffs
reference it, never contradict it silently.

## The handoff contract (`handoffN.md`)
- **Goal** — one sentence.
- **Operating rules** — the non-negotiables (see below).
- **Deliverables** — concrete, scoped.
- **Explicitly OUT of scope** — what NOT to build (prevents drift/over-build).
- **Acceptance criteria** — checkboxes; how "done" is judged.
- **Open questions** — what the Engineer must answer back.
- **Return format** — the shape of the handoffback.
- A **scope-management out** — "if it's too big, ship the core + flag the rest, and say what you deferred."

## The handoffback contract (`handoffbackN.md`)
- **Summary** + **file tree** + **how to run**.
- **Real test output** — pasted, not "tests pass."
- **Decisions & deviations** — where they diverged and why.
- **Blockers** — especially what didn't work.
- **Answers to the open questions.**
- **Where reality contradicted the design.**
- **Proposed scope for the next handoff** (Architect decides, but wants the Engineer's read).

## Operating rules (the disciplines that make it work)

Each rule exists because it prevents a specific failure. That's the whole point — copy the rules, not
just the flow.

| Rule | Failure it prevents | Real example (this project) |
|------|---------------------|------------------------------|
| **Verify against the real code + run the tests** (never trust the summary) | Summary-inflation — a report that says "works" over code that doesn't | Reading `react.py` confirmed ReAct was genuinely LLM-driven, not regex |
| **No fakes** — real APIs/models, no mocks/random in demos | Demo-rigging — a green demo that proves nothing | Enforced real Gemini + real Frankfurter throughout |
| **Function-first** — make it work end-to-end before measuring speed/cost | Premature optimization — validating perf on an unfinished system | We measured cache cost at H3 *before* the system ran end-to-end — it was the wrong order, and we corrected to function-first |
| **Measured, not tuned** — validation thresholds are measured, never hand-set to win | Self-deception — a benchmark you rigged to pass | H4 relaxed cache thresholds for a demo; flagged so they never leak into the A/B |
| **One bounded increment** + explicit out-of-scope | Scope creep / mush — a handoff that tries everything and does nothing well | Every handoff cut the Engineer's proposed scope to the critical path |
| **Honest deferral** — disclose stubs and partial work | Hidden debt — "done" that's half-done | H7 disclosed which "NOW" knobs were live vs stubbed |
| **Don't dramatize expected gaps** | False crisis — treating a normal early-stage gap as a strategic problem | "No traffic pre-launch" is normal, not a data emergency |

## When to use it
- Multi-step build where a human wants to stay in control of direction.
- You want each step tested and reviewed, not a big-bang generation.
- You're combining tools/agents for their strengths (architecture vs implementation).

## When NOT to
- Trivial one-shot changes (the contract overhead isn't worth it).
- Pure exploration where the goal isn't yet known (do that as a conversation first, then start the loop).

## The one thing that carries it
If you keep only one rule: **the Architect reviews the real artifact, not the report.** Everything else
degrades gracefully; that one doesn't. Skip it and the loop produces confident, plausible, wrong work.

---
*A technique, not a product. Reusable across projects — the roles and rules travel; the design doc is per-project.*
