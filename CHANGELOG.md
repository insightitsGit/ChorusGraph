# Changelog

All notable changes to ChorusGraph are documented here (semver).

## [1.0.0] — 2026-07-05 — Enterprise track (P1_Enterprice1)

### Added
- **E1–E4:** CI foundation, resilience, security, observability (see handoffbackE1–E4).
- **E5:** Durable SqliteGraphStore, migrations, backup/restore, right-to-forget.
- **E6:** Tenant isolation guards and resource limiter.
- **E7:** Load/throughput harness (`python -m benchmark.load`).
- **E8:** Product Dockerfile, docker-compose, k8s manifest, deploy docs.
- **E9:** Frozen public API (`chorusgraph/public.py`), stability guarantee, API 1.0 docs.

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
