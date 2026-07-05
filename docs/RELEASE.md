# Release process (E1)

ChorusGraph uses **semver** (`MAJOR.MINOR.PATCH`) in `pyproject.toml`.

## Pre-release checklist

1. All CI checks green on the release branch (deterministic `pytest`, ruff, mypy baseline, coverage ≥ floor).
2. Update `CHANGELOG.md` — move `[Unreleased]` items under the new version + date.
3. Bump `version` in `pyproject.toml`.
4. Verify pip install docs: [`docs/INSTALL.md`](INSTALL.md) (extras, PrismRAG plug-in guide).
5. Regenerate lockfile if dependencies changed:
   ```powershell
   pip install -U pip pip-tools
   pip-compile pyproject.toml -o requirements-lock.txt --extra dev --extra gemini --extra benchmark-healthcare
   ```
5. Regenerate SBOM:
   ```powershell
   cyclonedx-py environment -o sbom/release-sbom.json
   ```

## Tag and publish

```powershell
git tag -a v0.9.2 -m "v0.9.2 — short summary"
git push origin v0.9.2
```

GitHub Actions builds from the tag; attach `sbom/release-sbom.json` to the release artifact if publishing wheels.

## Test tiers

| Command | When | Needs |
|---------|------|-------|
| `pytest` | Every PR (CI default) | Nothing — cassettes replay, live tests excluded |
| `pytest -m live` | Manual / scheduled | `GEMINI_API_KEY`, network |
| `pytest -m live --run-benchmark` | Pre-canonical benchmark | Azure or local keys |

## Coverage floor

Configured in `pyproject.toml` → `[tool.coverage.report] fail_under`. Raise only when coverage genuinely improves — never lower without architect sign-off.
