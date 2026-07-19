# Changelog

All notable changes to ChorusGraph are documented here (semver).

## [1.3.0] — 2026-07-18

### Added
- **LLM call interceptors (ADR-008):** `NodeContext.call_llm`, `CompiledGraph.register_interceptor(before_llm=..., after_llm=...)`, `InterceptDecision` (proceed / halt / reroute), `Agent.with_interceptors`. Hooks fire at the provider boundary — not around whole BSP nodes. Opt-in; unmarked callables unchanged.
- **Cache force-refresh:** sidecar `must_revalidate`, `mark_revalidate(...)`, `Decision.force_refresh` + `created_at`. `CacheInterceptor` skips only when `is_hit and not force_refresh`. REPLAY_SAFE skip semantics unchanged when the bit is unset.
- **Warm public API:** `RetrievalBackend.bump_partition_version` / `get_chunk_vectors` (384-d `ChunkVectorRecord`) on PrismRAG + `ChorusStack` helpers. Keyword backend returns `{}` for vectors.
- **Ledger `kind` / `detail`:** optional fields on `LedgerStep`; Sqlite sink round-trip; `make_custom_step` for e.g. `shine.verdict`; `chorusgraph-audit` surfaces custom steps. Cache-gate steps record `created_at` / `force_refresh` in detail.
- **`consumes` metadata:** `Graph.add_node(..., consumes=[...])` → IR + `NodeContext.consumes`.
- **Encoder artifact id:** stamped on warm partition meta / retrieve chunks when `prismlang.encoder.model_id()` is available.
- **Docs:** [`ADR-008`](docs/ADR-008-llm-call-interceptors.md), CACHE_PROFILES §9, PLUGINS warm 384-d API.

### Changed
- Package version **1.3.0**.
- **Dependency floors:** `prismlang>=0.1.2`, `prismlib-plus>=0.8.0` (HitMeta / `CacheEntry.created_at` for cache-decision detail).
- **Cortex extra:** `prismcortex[prism-plus,gemini]>=0.3.0` — uses `[prism-plus]` (mutually exclusive with `[prism]`) so installs stay compatible with core `prismlib-plus`.
- **Cortex events:** `CortexMemoryService.on_event` / `bind_cache_revalidate` for PrismShine L1 force-refresh on corrections.
- **Note:** Standalone [`prismlib` 0.5.0](https://pypi.org/project/prismlib/0.5.0/) is the open-core twin; ChorusGraph consumes the `prism` namespace via **prismlib-plus** and must not install both extras.

## [1.0.0] — 2026-07-05 — Enterprise track (P1_Enterprice1)

### Added
- **E1–E4:** CI foundation, resilience, security, observability (see handoffbackE1–E4).
- **E5:** Durable SqliteGraphStore, migrations, backup/restore, right-to-forget.
- **E6:** Tenant isolation guards and resource limiter.
- **E7:** Load/throughput harness (`python -m benchmark.load`).
- **E8:** Product Dockerfile, docker-compose, k8s manifest, deploy docs.
- **E9:** Frozen public API (`chorusgraph/public.py`), stability guarantee, API 1.0 docs.

## [1.2.0] — 2026-07-17

Published on PyPI: [chorusgraph 1.2.0](https://pypi.org/project/chorusgraph/1.2.0/).

### Added
- **L1 single-flight (opt-in):** in-process miss coalescing for `exact`/`fingerprint` keys under `global`/`tenant` scope — one leader computes; followers join or time out ([`ADR-006`](docs/ADR-006-l1-single-flight.md)). Default **off**. Enable via `CacheProfile(single_flight=True)` or `ChorusStack.with_flight(FlightPolicy(enabled=True))`.
- **Docs:** [`LOOP-TOKEN-BURN-FINDINGS.md`](docs/LOOP-TOKEN-BURN-FINDINGS.md), ADR-006, ADR-007.

### Changed
- **ReAct anti-thrash default:** `ReActOpts.stop_on_repeated_action` now defaults to `True` (exact tool+args replay stops the loop). Opt out with `False` for intentional retries ([`ADR-007`](docs/ADR-007-react-repeated-action-default.md)).
- **SidecarStore:** thread-safe SQLite access for concurrent gate lookups under single-flight.
- **Docs & website:** canonical MVP benchmark updated to Azure run `mid_20260708_111539` (100 tasks/scenario) with latency/LLM summary. Supersedes `20260704_212111` for public claims.

### Fixed
- **Benchmark comparison:** `abstain_rate` now uses `lower_is_better=True` (fewer refusals wins).

## [Unreleased]

## [1.1.0] — 2026-07-13

Published on PyPI: [chorusgraph 1.1.0](https://pypi.org/project/chorusgraph/1.1.0/).

### Added
- **Optional warm chunk vectors (L2):** for production RAG that reuses a knowledge corpus, index
  once by `partition`/`version`, warm at worker boot (`ChorusStack.warm_retrieval` /
  `retrieval_ready`), attach `vector_64` on retrieve, and opt into `rerank_policy="vectors_only"`
  (or `require`) so Resonance rerank never silently re-embeds chunks. Cuts multi-second corpus
  re-encode taxes and keeps markdown warm when the product catalog changes. **Defaults preserve
  1.0.x behavior** (`rerank_policy="embed_missing"`). See [`docs/ADR-005-warm-chunk-vectors.md`](docs/ADR-005-warm-chunk-vectors.md)
  and [`docs/PLUGINS.md`](docs/PLUGINS.md).
  Smoke: `python scripts/smoke_warm_chunk_vectors.py`.

## [1.0.3] — 2026-07-06

### Added
- **`chorusgraph-audit` CLI:** cold log simulation for cache hit-rate and cost estimates (no API key);
  ledger-backed pilot reports via `--ledger` / `--list-runs`.
- **Enterprise Postgres persistence port:** `PostgresGraphStore` and migrations for durable graph state.
- **Licensing module:** key validation hooks for enterprise deployments.
- **Package data:** ship default section profiles and shadow replay fixtures with the wheel.

### Changed
- Add `cryptography` to core dependencies.
- Repo hygiene: stop tracking local virtualenvs and `dist_pkg_test` build artifacts.

## [1.0.2] — 2026-07-06

### Fixed
- **`dict_node_adapter` resonance slug collision (Bug-2):** default `category_slug` now uses the node id
  (`hop`) instead of shared state `route`, so downstream nodes no longer tune to the same frequency when
  a router value (e.g. `site_kb`) flows through the graph. Opt-in legacy behavior:
  `category_slug_from="route"`. Found via real Website Hub production migration — see
  `handoffs/handoffBug2_dict_node_adapter.md`.

## [1.0.1] — 2026-07-05

### Fixed
- **Clean install:** add `prismlib-plus` and `prismresonance` to core dependencies so `pip install chorusgraph` succeeds and `import chorusgraph` works without optional extras.
- **Python floor:** require Python ≥3.11 (matches `prismlib-plus`).

## [Unreleased]

### Changed
- Canonical MVP benchmark pointer updated to Azure run `20260704_212111` (HC2 87.5% vs HL2 57.5%).

## [0.9.1] — 2026-07-03

### Added
- HC2 Bug-1 fix: depth-aware cache replay routing (facts-only archetype C).
- Azure benchmark image includes `chromadb` for healthcare vector retrieval.
- H21 CacheProfile engine (T1–T7) with offline HC1 cache proof.

### Fixed
- HC2 healthcare-multi success regression (45% → 87.5% on canonical run).

## [0.9.0] — MVP benchmark milestone

- Native `core.Graph` engine for FC/HC scenarios.
- 8-scenario LangGraph vs ChorusGraph benchmark matrix.
