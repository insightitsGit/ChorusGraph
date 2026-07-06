# Handoff Bug-2 — `dict_node_adapter` resonance-slug collision (real production find, v1.0.2)

**Director:** Amin · **Repo:** ChorusGraph (this repo) · **Source:** live dogfood migration of a real
production agent ("Website Hub," `C:\code\InsightitsAIAgent\meeting-scheduler`) from LangGraph to
ChorusGraph 1.0.1, using Cursor with no scripted prompt — a genuine, unscripted real-world test.

**Why this matters:** the engineer doing that migration hit a real correctness bug in the shipped
library and worked around it by writing a custom adapter instead of using the built-in
`dict_node_adapter`. Confirmed by direct comparison of their custom adapter's docstring against the
installed package's source — this is not a hypothetical, it already bit a real user.

---

## 0. The bug, precisely

**File:** `chorusgraph/core/node.py`, `dict_node_adapter()` (currently line ~125).

```python
update = ctx.publish(
    artifact=artifact,
    rule_chain=list(result.get("rule_chain") or []),
    category_slug=str(result.get("route") or result.get("category_slug") or hop),   # <-- the bug
)
```

**The problem:** the adapter uses the node's *own result dict's* `route` field — if present — as that
node's Resonance category_slug. But `route` is commonly a value set by an upstream router node and
carried through shared graph state, not something specific to the current node. In a real production
graph (the Website Hub agent: `classify_intent` routes to one of several branches including `site_kb`),
multiple *different* downstream nodes can end up publishing envelopes with the *same* `route` value
still present in their result dict. Using it as the category_slug means the Resonance bus treats
unrelated nodes as tuned to the same frequency — exactly the "shared route values fan out to every node
on that slug" failure the real customer's own docstring names.

**The customer's fix (verified, in their own words, from their custom adapter's docstring):**
> "Uses the node id (hop) as the resonance slug — not `route` — so shared route values like `site_kb`
> do not fan out to every node on that slug."

That is, key on the node's own identity (`hop`) — never on a value that flows through shared state and
can collide across nodes.

---

## T1 — Fix `dict_node_adapter`'s default category_slug behavior

**File:** `chorusgraph/core/node.py`

1. Change the default to key on `hop` first, with an explicit opt-in to the old `route`-based behavior
   for anyone who genuinely wants it (some existing caller, however unlikely, might depend on the current
   behavior in a graph shape where it happens not to collide — don't break them silently):

   ```python
   def dict_node_adapter(
       fn: Callable[[Dict[str, Any]], Dict[str, Any]],
       *,
       hop: str,
       category_slug_from: str = "hop",   # "hop" (safe default) | "route" (legacy/opt-in)
   ) -> NodeFn:
       ...
       if category_slug_from == "route":
           slug = str(result.get("route") or result.get("category_slug") or hop)
       else:
           slug = str(result.get("category_slug") or hop)   # never `route` by default
       update = ctx.publish(..., category_slug=slug)
   ```

   Verify this exact signature against the real current code before implementing — read the full
   function fresh, don't assume this snippet is byte-for-byte final; it's the fix's intent, not a diff
   to paste blindly.
2. Update the docstring to explain *why* — reference the collision scenario directly (a router value
   shared across nodes), not just "changed the default," so the next person reading this code
   understands the reasoning, same as the customer's own docstring did.
3. This is a genuine **bug fix, not a new feature** — `docs/STABILITY.md` classifies this as PATCH
   ("bug fixes, no API changes"). The signature gains an optional keyword-only parameter with a
   backward-safe default path available via `category_slug_from="route"` — existing call sites using
   only `fn`/`hop` positionally-or-keyword continue to work, just with corrected (safer) default
   behavior. Confirm this reasoning holds before treating it as anything other than PATCH.

**Exit criteria:**
- New test reproducing the exact collision: two nodes in a graph, both fed a result dict containing the
  same `route` value (simulating state carrying a router's decision downstream) but different
  `category_slug`-relevant identities — assert they resolve to **different** Resonance frequencies via
  `hop`, not the shared `route` value.
- Existing `dict_node_adapter` tests (search the suite for current coverage) still pass.
- `category_slug_from="route"` opt-in path tested and produces the old behavior exactly, for anyone who
  needs it.

---

## T2 — Version bump + re-publish (this is a NEW version, not an update to 1.0.1)

**Confirmed with the Director:** PyPI (like virtually every package registry) never allows re-uploading
content under an already-published version string — `1.0.1` is permanent as-is. This fix ships as
**`1.0.2`** — a PATCH bump per `docs/STABILITY.md`'s own policy, since it's a bug fix with no breaking
API change (see T1.3's reasoning).

1. Bump `version = "1.0.1"` → `"1.0.2"` in `pyproject.toml`.
2. Bump `chorusgraph/__init__.py`'s `__version__` to match (confirm both are always kept in lockstep —
   check how `1.0.1` was bumped last time for the exact pattern).
3. Add a `CHANGELOG.md` entry under a new `## [1.0.2]` heading: describe the bug (resonance-slug
   collision on shared `route` values), the fix (default to `hop`), and the new
   `category_slug_from` opt-in parameter. Reference this handoff.
4. Build and publish: `python -m build` then upload via whatever mechanism published `1.0.1` (confirm
   the exact publish command/credentials setup from that prior release rather than guessing).
5. **Re-run the exact clean-room verification used for 1.0.1** before considering this done:
   ```powershell
   python -m venv clean_test_env
   clean_test_env\Scripts\pip install chorusgraph==1.0.2
   clean_test_env\Scripts\python -c "import chorusgraph; from chorusgraph import Graph, ChorusStack; print(chorusgraph.__version__)"
   ```
   This must print `1.0.2` and succeed exactly as `1.0.1` did — don't assume the packaging is fine
   just because the code change is small.

**Exit criteria:** `pip install chorusgraph==1.0.2` from a clean venv succeeds, imports correctly, and
the T1 collision test passes against the *installed* package (not just the local repo) — install it
fresh and run the new test against that install, not just in-repo.

---

## T3 — Backward-compat aliasing pattern → migration prompt guidance

**File:** `docs/AI_IDE_PROMPTS.md`

The Website Hub migration invented a genuinely good pattern worth codifying for future clients rather
than making each one rediscover it: **during a LangGraph→ChorusGraph migration, keep old
diagnostic/health-check keys and environment-variable names aliased to the new ones**, so nothing
downstream (dashboards, monitoring, existing deploy configs) breaks silently. Concretely, what the real
migration did:
- A health-check response exposing both `'chorusgraph'` and a legacy `'langgraph'` key pointing at the
  same status data.
- A `use_langgraph()` function kept as an explicit, documented alias for `use_chorusgraph()`.
- An environment-variable check accepting both the new name and the legacy name
  (e.g., `WEBSITE_HUB_USE_CHORUSGRAPH` and `WEBSITE_HUB_USE_LANGGRAPH`).

Add a step to **Prompt 2** (the migration prompt) instructing the AI IDE assistant to apply this same
aliasing pattern wherever the existing codebase exposes LangGraph-named diagnostics, health checks, or
config flags — don't rename-and-break, alias-and-preserve.

**Exit criteria:** `docs/AI_IDE_PROMPTS.md` Prompt 2 includes this guidance explicitly, with the real
example above as illustration (it's a proven pattern from an actual migration, not theoretical).

---

## Non-goals

- Do not go hunting for every other possible default-behavior bug in the compat/adapter layer as part of
  this handoff — this is a scoped fix for the one confirmed, real issue. If you notice something else
  while in this code, flag it in the return rather than silently expanding scope.
- Do not rename `dict_node_adapter` or change its core purpose — it's explicitly documented as a
  "temporary bridge... prefer native NodeFn for new graphs." That framing stays.

## Return format (`handoffbackBug2.md`)

- Files changed · exit criteria pass/fail with real command output.
- The exact new `category_slug_from` signature as implemented (confirm it matches or explain the
  deviation from this handoff's proposal).
- The T2 clean-room verification output against the *published* `1.0.2`, not just local code.
- Confirmation `docs/AI_IDE_PROMPTS.md` was updated with the real example, not a generic paraphrase.
- Anything left undone, stated plainly. No commits/publish beyond what's asked — confirm with the
  Director before the actual `pip upload`/publish step specifically, since that's a public, irreversible
  action (a version, once published, can never be replaced).

---
*Bug-2 · found via real production dogfooding, not a synthetic test · fixes a genuine Resonance-slug
collision in the shipped adapter · ships as 1.0.2, a real new PyPI version, since 1.0.1 can never be
overwritten · also codifies the migration's backward-compat-aliasing pattern for future clients.*
