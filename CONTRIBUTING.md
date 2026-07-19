# Contributing to ChorusGraph

Thank you for helping improve ChorusGraph. This project is the **native agent
runtime** (engine, Prism stack, benchmarks) — not a LangGraph wrapper. Please
read [`docs/TERMINOLOGY.md`](docs/TERMINOLOGY.md) before changing orchestration
or benchmark code.

## Ways to contribute

- **Bug reports** — reproducible steps, version, Python version
- **Feature requests** — describe the use case and which layer is affected
  (engine, cache, retrieval, memory, benchmarks, docs)
- **Pull requests** — bug fixes, tests, docs, examples, benchmark improvements
- **Benchmarks** — follow [`benchmark/SCENARIOS.md`](benchmark/SCENARIOS.md) and
  the FC/HC vs FL/HL matrix

## Before you start

1. Check [open issues](https://github.com/insightitsGit/ChorusGraph/issues) and
   [pull requests](https://github.com/insightitsGit/ChorusGraph/pulls) for
   duplicates.
2. For large changes, open an issue first so we can align on design.
3. Read [`AGENTS.md`](AGENTS.md) (terminology and hard rules for AI-assisted
   edits) and [`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md) for product
   patterns.

## Hard rules (orchestration)

| Prefix | Meaning | Framework |
|--------|---------|-----------|
| **FC***, **HC*** | ChorusGraph native | `chorusgraph.core.Graph` only |
| **FL***, **HL*** | LangGraph baselines | `langgraph.graph.StateGraph` |

**Do not** add `langgraph` imports under `benchmark/fc*`, `benchmark/hc*`, or FC1
graph builders. CI enforces this via
[`tests/test_fc_hc_no_langgraph.py`](tests/test_fc_hc_no_langgraph.py).

LangGraph is for **baseline comparison** and legacy `wrap()` migration only.

## Development setup

**Requirements:** Python 3.11+

```bash
git clone https://github.com/insightitsGit/ChorusGraph.git
cd ChorusGraph
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -U pip setuptools wheel
pip install -e ".[dev,gemini,benchmark-healthcare,cortex]"
pip install "prismlib-plus>=0.8.0" "prismlang>=0.1.2"
```

See [`docs/INSTALL.md`](docs/INSTALL.md) for optional extras (`retrieval`,
`postgres`, `benchmark`, etc.).

## Running checks locally

Match what CI runs on every push:

```bash
# Lint + format (tests and .github scope)
ruff check tests .github
ruff format --check tests .github

# Deterministic tests — no API keys, no network
set CHORUSGRAPH_DETERMINISTIC=1
set GEMINI_API_KEY=
set GOOGLE_API_KEY=
pytest tests -q --timeout=120 --cov=chorusgraph --cov=benchmark
```

On Linux/macOS, use `export` instead of `set`.

**Live Gemini tests** (optional, not run in default CI):

```bash
export CHORUSGRAPH_LIVE=1
export GEMINI_API_KEY=your_key
pytest tests -m live -q
```

**Mypy** runs in CI with `continue-on-error` while legacy type debt is cleared;
fix new type issues when you touch a module.

## Pull request checklist

- [ ] Branch is up to date with `master`
- [ ] `ruff check tests .github` and `ruff format --check tests .github` pass
- [ ] `pytest tests` passes with `CHORUSGRAPH_DETERMINISTIC=1` and empty API keys
- [ ] FC/HC paths do not import LangGraph
- [ ] Docs updated if behavior, public API, or benchmark semantics change
- [ ] [`CHANGELOG.md`](CHANGELOG.md) updated for user-visible changes (if
      applicable)
- [ ] No secrets, `.env` values, or API keys committed

Use the [pull request template](.github/PULL_REQUEST_TEMPLATE.md) when opening a
PR.

## Code style

- Follow existing patterns in the module you edit.
- Prefer focused diffs — avoid drive-by refactors.
- Comments explain *why*, not *what*, when the logic is non-obvious.
- Public API changes must respect [`docs/STABILITY.md`](docs/STABILITY.md) and
  [`docs/API_1_0.md`](docs/API_1_0.md).

## Benchmarks

- Native scenarios: **FC1, FC2, HC1, HC2** — compile with `Graph.compile()`
- Baselines: **FL1, FL2, HL1, HL2** — LangGraph only
- Compare paired results with [`benchmark/compare_scenarios.py`](benchmark/compare_scenarios.py)
- Document run IDs and tier (`light` / `mid` / `heavy`) in PR description when
  submitting result archives

Do not commit invalid or quota-exhausted benchmark runs.

## Documentation

- Product docs live under [`docs/`](docs/)
- README benchmark tables should point at canonical run IDs in
  [`benchmark/results/`](benchmark/results/)
- When docs say "ChorusGraph", they mean the **full native product** — see
  terminology policy

## Security

Report vulnerabilities privately — see [`SECURITY.md`](SECURITY.md). Do not
file security issues in the public tracker.

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By
participating, you agree to uphold it.

## License

By contributing, you agree that your contributions will be licensed under the
[Apache License 2.0](LICENSE).
