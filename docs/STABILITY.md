# ChorusGraph 1.0 Stability Guarantee

**Effective:** Release 1.0.0 · **Package:** `chorusgraph`

## Guarantee

Semver 1.x public API symbols listed in `chorusgraph/public.py` and `docs/API_1_0.md` will remain backward-compatible for the lifetime of the 1.x series.

## Versioning policy

- **PATCH** — bug fixes, no API changes
- **MINOR** — additive API only (new optional parameters, new modules)
- **MAJOR** — breaking changes (2.0+)

Deprecated APIs receive one minor release warning via docstring before removal.

## Namespace

**Decision:** Primary package remains `chorusgraph`. Optional Prism extras (`prismcortex`, `prismlang`) stay separate dependencies — not merged into `prismlib-plus[orchestrator]` for 1.0.

## Migration from 0.x

1. Pin `chorusgraph>=1.0,<2`.
2. Replace direct `InMemoryGraphStore` assumptions — durable graph is default via `CortexMemoryService(durable_graph=True)`.
3. CI: use default `pytest` (deterministic tier); live tests behind `-m live`.
4. Deploy: follow `docs/DEPLOY.md` with `CHORUSGRAPH_PG_DSN`.

## Non-goals for 1.0

- Full Postgres Cortex GraphStore (SQLite durable store ships; Postgres connector Phase 2)
- Audited CHORUS cipher (TLS default; cipher opt-in only)
