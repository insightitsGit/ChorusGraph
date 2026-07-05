# Changelog

All notable changes to ChorusGraph are documented here (semver).

## [Unreleased] — Enterprise track (P1_Enterprice1)

### Added
- **E1:** Deterministic CI test tier — Frankfurter HTTP cassettes replay without network; live Gemini tests behind `pytest -m live`.
- **E1:** GitHub Actions CI — ruff, mypy baseline, pytest + coverage floor (71%), CycloneDX SBOM artifact.
- **E1:** `requirements-lock.txt` for reproducible installs; `docs/RELEASE.md` release process.

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
