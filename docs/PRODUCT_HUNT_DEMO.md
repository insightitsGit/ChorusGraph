# Product Hunt — interactive demo

**Canonical demo URL:** https://insightitsGit.github.io/ChorusGraph/demo.html

Paste this into Product Hunt → **Interactive demo (optional)**.

## What it is

A **try-it playground** (not a slide deck): pick a mode, type a question, stream a simulated Route Ledger. Repeat an FX question to see **PrismCache HIT**. No API key.

Canonical URL: https://insightitsGit.github.io/ChorusGraph/demo.html

## Modes you can run in the browser

| Mode | What you see |
|------|----------------|
| Cache | MISS → tools → seed; same query again → HIT (~ms) |
| ReAct | Thought / tool / observation loop; seeds cache |
| Plan-Solve | Static plan then steps |
| Reflection | Wrong draft rejected, then approved |
| Multi-agent | researcher → writer → validator |
| Warm chunks | partition retrieve + isolation note |
| Cortex | digest then recall (right lifecycle) |

## Run locally (browser)

```bash
cd website
python -m http.server 8080
# http://localhost:8080/demo.html
```

## Real Python engine (offline CLI)

```bash
pip install -e .
chorusgraph-use-cases
chorusgraph-use-cases cache
chorusgraph-use-cases warm_chunks
chorusgraph-use-cases cortex
```

## Product Hunt checklist

- [ ] Interactive demo URL → `https://insightitsGit.github.io/ChorusGraph/demo.html`
- [ ] Primary CTA → GitHub repo or `pip install chorusgraph`
- [ ] README links to demo
- [ ] Repo **About** website → demo URL or landing root
