# Handoff 3 — Return · Senior Engineer (Cursor) → Architect

## 1. Summary

Built **production shadow replay** (`chorusgraph/shadow/replay/`) with JSONL ingest, **70/30 temporal split** (seed earlier traffic → evaluate later), reuse of H2 `gate()` unchanged, and **statistical rigor**: Wilson/Clopper-Pearson FP upper bounds, `MIN_HITS=300` gate, verdicts `CACHEABLE` / `INSUFFICIENT DATA` / `UNSAFE`.

Pulled a **real** `website_chat_turns` export from production (`vm-insightits-prod` Docker Postgres, `meeting_scheduler` DB — **102 turns total**). Azure CLI used to reach the VM; Key Vault `database-url` points at `insight_hospital` on Azure Flexible Server which does **not** contain `website_chat_turns`.

**Go/no-go result:** No slug is `CACHEABLE` — eval volume (~9–31 turns per slug at full 102) is orders of magnitude below `MIN_HITS=300`. Point estimates look safe (FP=0 where hits exist) but we **cannot bless any threshold** statistically. The cost thesis remains **unvalidated** until more traffic accumulates or MIN_HITS is lowered for early pilot (not recommended without director sign-off).

## 2. File tree

```
chorusgraph/shadow/replay/
├── __init__.py
├── SCHEMA.md                    # JSONL schema + director export SQL
├── schema.py                    # TurnRecord
├── ingest.py                    # load_jsonl()
├── policies.py                  # route → CachePolicy
├── stats.py                     # Wilson/Clopper-Pearson, MIN_HITS, Verdict
├── replay.py                    # temporal_split(), run_temporal_replay()
├── report.py                    # format_production_report()
├── cli.py                       # chorusgraph-replay entrypoint
└── data/
    └── website_chat_turns.jsonl # 27/102 turns exported (see blockers)

scripts/
├── download_turns_chunked.py    # Azure VM → JSONL (chunked base64)
├── export_from_keyvault.py      # Key Vault path (wrong DB for website hub)
├── list_chat_tables.py
└── vm_count_turns.sh            # confirmed 102 turns on prod VM

tests/test_replay.py
handoffs/handoffback3.md
```

## 3. How to run

```powershell
cd C:\code\ChorusGraph
pip install -e ".[dev]"

# Production replay (requires JSONL export)
python -m chorusgraph.shadow.replay.cli
# or: chorusgraph-replay --jsonl chorusgraph/shadow/replay/data/website_chat_turns.jsonl

# Re-export from prod VM (Amin / ops)
python scripts/download_turns_chunked.py

# Full test suite
pytest -v
```

**Director export SQL** (run on `vm-insightits-prod` docker `postgres` / `meeting_scheduler`):

```sql
SELECT user_message AS query,
       COALESCE(NULLIF(route,''), 'general') AS category_slug,
       assistant_message AS response,
       created_at AS timestamp,
       id AS section_id
FROM website_chat_turns
WHERE assistant_message IS NOT NULL AND assistant_message <> ''
ORDER BY created_at ASC;
```

## 4. Test results

```
======================== 27 passed, 1 skipped in ~3.4s ========================
```

Includes `test_replay_on_production_export` against real downloaded JSONL.

### Production shadow report (27 turns, 18 seed / 9 eval, COARSE=0.88)

```
Production shadow replay — website_chat_turns.jsonl
seed_turns=18 eval_turns=9 (temporal split; shadow only, never served)
MIN_HITS for CACHEABLE verdict: 300
================================================================================================
slug           verify       h      FP  FP_up95  serve  fp_n     n verdict
------------------------------------------------------------------------------------------------
general          0.90   0.000   0.000    1.000      0     0     1 INSUFFICIENT DATA
...
greeting         0.90   1.000   0.000    0.950      1     0     1 INSUFFICIENT DATA
greeting         0.95   1.000   0.000    0.950      1     0     1 INSUFFICIENT DATA
...
needs_web        0.90   0.000   0.000    1.000      0     0     5 INSUFFICIENT DATA
...
site_kb          0.90   0.500   0.000    0.950      1     0     2 INSUFFICIENT DATA
site_kb          0.93   0.500   0.000    0.950      1     0     2 INSUFFICIENT DATA
site_kb          0.95   0.000   0.000    1.000      0     0     2 INSUFFICIENT DATA
...
------------------------------------------------------------------------------------------------
No slug/threshold pair is CACHEABLE (insufficient n or FP bound too high).

Semantic coverage gap: 0 would-serve hits on SEMANTIC policy (excluded from FP numerator).
```

**Observations on real traffic:**
- `greeting` eval: 1 fp-eligible hit, correct match (h=1.0, FP=0) — but n=1 → `INSUFFICIENT DATA`
- `site_kb` eval: 1 hit at verify 0.90–0.93, correct match — n=1 → `INSUFFICIENT DATA`
- `needs_web`, `general`: 0 hits at coarse 0.88 on eval slice
- Full DB has **102 turns** — even at 100% export, max eval ≈ 31 turns; per-slug n ≪ 300

## 5. Key decisions & deviations

| Decision | Rationale |
|----------|-----------|
| **Real source = EC2 VM Docker Postgres** | Handoff §3.1 assumes Azure Flexible Server; Key Vault `database-url` → `insight_hospital` has no `website_chat_turns` (only empty `ai_chat_observations`). Website hub logs live in `meeting_scheduler` on `vm-insightits-prod` (`docker exec postgres`). |
| **Route → cache policy mapping** | `greeting`→EXACT, `site_kb`/`needs_web`→REPLAY_SAFE, `general`→SEMANTIC per DESIGN §8. |
| **FP ground truth = structural string match** | Compare would-serve cached response vs eval turn's actual `assistant_message` (normalized whitespace). |
| **Clopper-Pearson upper bound** | Falls back to Wilson if `scipy` absent; both implemented in `stats.py`. |
| **MIN_HITS=300 enforced** | Per §3.3 — no slug recommended as CACHEABLE on this volume. |
| **Partial export (27/102)** | `az vm run-command` truncates large stdout; chunk download fails on turns with heavy JSON escaping. Full export needs `psql \copy` to blob storage or SSH tunnel (see blockers). |
| **Dashboard hub** | No `dashboard_chat_turns` (or equivalent) found in repo schema — Website Hub only for H3. |

## 6. Blockers / issues hit

1. **Wrong Azure Postgres for website hub** — `psql-insight-hospital-prod` / `insight_hospital` is InsightHospital, not meeting-scheduler. Website hub turns are on the prod VM.
2. **Traffic volume** — 102 total turns is far below `MIN_HITS=300`. Cannot produce a statistically valid `(h, FP)` frontier; all slugs `INSUFFICIENT DATA`.
3. **Export mechanism** — Chunked `az vm run-command` + base64 works for small turns; ~75 turns failed JSON parse (embedded quotes/newlines in assistant responses). Need director to run `\copy` to Azure Blob or open SSH tunnel for full dump.
4. **EC2 `44.198.45.191:5432` timeout** from local — firewall; VM run-command works.
5. **AWS S3 DB dump** — credentials invalid locally; not used.

## 7. Answers to §6 open questions

### Q1 — Real per-slug `(h, FP_upper95)` frontier. Which slugs CACHEABLE?

| slug | best h (verify) | FP_point | FP_upper95 | n_would_serve (eval) | verdict |
|------|-----------------|----------|------------|----------------------|---------|
| greeting | 1.0 @ all | 0.0 | 0.95 | 1 | INSUFFICIENT DATA |
| site_kb | 0.5 @ 0.90–0.93 | 0.0 | 0.95 | 1 | INSUFFICIENT DATA |
| needs_web | 0.0 | — | 1.0 | 0 | INSUFFICIENT DATA |
| general | 0.0 | — | 1.0 | 0 | INSUFFICIENT DATA |

**None CACHEABLE.** At full 102-turn export, still INSUFFICIENT DATA everywhere (n ≪ 300).

### Q2 — Semantic coverage gap / generative-judge urgency?

**0 would-serve hits** on `SEMANTIC` (`general` route) in eval slice at coarse 0.88. Generative-judge handoff is **not urgent yet** — no measurable semantic savings to protect. Revisit when `general` route produces fp-eligible hits under shadow.

### Q3 — Recommended production COARSE/VERIFY per cacheable slug?

**None recommended for live enable.** If director approves a **pilot** before MIN_HITS is met:
- Start shadow-only with **COARSE=0.88, VERIFY=0.93**
- Watch `site_kb` and `greeting` first (only slugs with observed hits)
- Do **not** enable live serve until n_would_serve ≥ 300 and FP_upper95 < 1%

### Q4 — Slugs to cut?

**Not cut on safety grounds** (no FPs observed). **Cut on ROI grounds:** `needs_web` and `general` show h=0 at 0.88 on current volume — low priority for cache investment until traffic grows.

### Q5 — Proposed H4 scope

1. **Full log export pipeline** — SSH tunnel or `\copy` → Blob; target 10k+ turns before re-measuring.
2. **Enable live cache (shadow-flag off)** per slug only after CACHEABLE verdict — gated on this handoff.
3. **PrismCheckpointer** skeleton (§4 out of scope for H3).
4. **FAQ baseline comparison** — `normalized_question` exact-match reuse vs semantic gate (§3.1 bonus).
5. **Generative LLM-judge** — defer until semantic hits > 0 in shadow.

## 8. Design contradictions

1. **§3.1 "thousands of turns"** — production DB has 102. Volume assumption in handoff exceeds reality.
2. **§7 Azure Flexible Server** — website hub logs are on VM Docker Postgres, not the Flexible Server named in handoff. Schema doc updated in `SCHEMA.md`.
3. **Dashboard hub equivalent table** — not confirmed in codebase; H3 is Website Hub only.

## 9. Proposed H4 scope

See §7 Q5. **Critical path:** accumulate traffic → re-run `chorusgraph-replay` → first CACHEABLE slug → then live enable + PrismCheckpointer.

---

*Handoff 3 complete · 27 pytest passed · real prod replay · all slugs INSUFFICIENT DATA · cache NOT cleared for live serve.*
