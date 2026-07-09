## Summary

<!-- What changed and why? Link issues with "Fixes #123" when applicable. -->

## Type of change

- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change (explain in Summary + CHANGELOG)
- [ ] Documentation only
- [ ] Benchmarks / results archive
- [ ] CI / tooling

## Terminology & orchestration

- [ ] I read [`docs/TERMINOLOGY.md`](../docs/TERMINOLOGY.md)
- [ ] FC/HC paths use `chorusgraph.core.Graph` only (no new `langgraph` imports)
- [ ] FL/HL baseline changes are isolated to `benchmark/fl*` / `benchmark/hl*`

## Testing

- [ ] `ruff check tests .github` passes
- [ ] `ruff format --check tests .github` passes
- [ ] `pytest tests` passes with `CHORUSGRAPH_DETERMINISTIC=1` and empty `GEMINI_API_KEY` / `GOOGLE_API_KEY`
- [ ] Live tests run locally (if this PR touches Gemini/live paths): `pytest tests -m live`

## Docs & release

- [ ] User-visible changes noted in [`CHANGELOG.md`](../CHANGELOG.md) (if applicable)
- [ ] Public API changes respect [`docs/STABILITY.md`](../docs/STABILITY.md)
- [ ] No secrets, `.env` values, or customer data committed

## Benchmarks (if applicable)

<!-- Run ID, tier (light/mid/heavy), scenario prefix, and whether results are canonical -->
