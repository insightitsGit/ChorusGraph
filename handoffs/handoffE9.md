# Handoff E9 — API 1.0

**From:** Architect (Claude) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Design reference:** [`../docs/ENTERPRISE_READINESS.md`](../docs/ENTERPRISE_READINESS.md) **§E9** · DESIGN §17 (open packaging question) · [`../docs/PROCESS.md`](../docs/PROCESS.md).
**Depends on:** E1–E8. **Return in:** `handoffs/handoffbackE9.md`.

The last enterprise handoff — turns a 0.x library into a 1.0 product with a stability guarantee.

## 0. Operating rules
No fakes; recorded fixtures. One bounded increment. Breaking changes allowed **only** to reach a clean 1.0 surface, all documented.

## 1. Goal
A stable, fully documented **1.0** public API.

## 2. Deliverables
- **Freeze the public API surface** — decide what's public vs internal; a deprecation/versioning policy.
- **Reference docs** — docstrings → published API docs (mkdocs/sphinx) + a quickstart + tutorials.
- **Namespace decision** — resolve `chorusgraph` vs `prismlib-plus[orchestrator]` (the long-open §17 director question).
- **1.0 release** — tagged, with a written stability guarantee + migration notes from 0.x.

## 3. Out of scope
E1–E8 · MVP fixes · new product features (1.0 is a stabilization, not a feature release).

## 4. Acceptance criteria
- [ ] Public API surface frozen + documented; internal APIs marked as such.
- [ ] Versioning/deprecation policy written.
- [ ] Complete published reference docs + quickstart; examples run against 1.0.
- [ ] Packaging namespace decided (Director sign-off) and applied.
- [ ] A **1.0** release tagged with a stability guarantee + 0.x→1.0 migration notes.

## 5. Open questions for handoffbackE9
1. What's in vs out of the public surface (proposed).
2. Docs tooling (mkdocs / sphinx).
3. Namespace recommendation for the Director's decision.
4. Any breaking changes needed to reach a clean 1.0.

## 6. Return format
Summary · file tree · how to run (docs build + examples) · decisions/deviations · blockers · answers to §5 · release notes.

---
*Handoff E9 · enterprise track · API 1.0 · stability guarantee + complete docs.*
