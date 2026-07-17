# Product Hunt — interactive demo

**Canonical demo URL:** https://insightitsGit.github.io/ChorusGraph/demo.html

Paste this into Product Hunt → **Interactive demo (optional)**.

## What it shows (11 steps)

1. Problem — token burn, audit gap, integration tax  
2. `pip install chorusgraph` — `ChorusStack.defaults()` attaches **PrismCache** + Cortex  
3. `chorusgraph-demo` — native routing, no API key  
4. Route Ledger — per-hop `rule_chain` (includes cache decisions)  
5. **Built-in semantic cache** — interactive **miss / hit** toggle  
6. **Warm chunks (L2) & PrismCortex (L3)** — interactive toggle:
   - Warm: `index(partition, version)` → `warm_retrieval` → query-only retrieve  
   - Cortex: recall at ingress · async `schedule_digest` (wrong vs right)  
7. **Use cases & design patterns** — tabs for ReAct · Plan-Solve · Reflection · Multi-agent · Cache · Warm · Cortex  
8. Multi-agent role pipeline  
9. Optional live Gemini: `chorusgraph-finance-patterns` / `chorusgraph-finance-memory`  
10. `chorusgraph-audit` — real semantic gate on your query logs  
11. Verified benchmarks + GitHub CTAs  

## Run locally (browser)

```bash
cd website
python -m http.server 8080
# http://localhost:8080/demo.html
```

## Run locally (CLI use cases — no API key)

```bash
pip install -e .
chorusgraph-use-cases                 # all seven
chorusgraph-use-cases cache
chorusgraph-use-cases warm_chunks
chorusgraph-use-cases cortex
chorusgraph-use-cases react
chorusgraph-use-cases plan_solve
chorusgraph-use-cases reflection
chorusgraph-use-cases multi_agent
chorusgraph-audit --log tests/fixtures/audit_cold_queries.jsonl
```

## Optional polish

Record the same flow in [Supademo](https://supademo.com/) or [Arcade](https://arcade.software/) (free for PH launches) and embed via iframe on `website/demo.html` if you want hotspot-style interaction.

## Product Hunt checklist

- [ ] Interactive demo URL → `https://insightitsGit.github.io/ChorusGraph/demo.html`
- [ ] Primary CTA → GitHub repo or `pip install chorusgraph`
- [ ] README links to demo (done on `master`)
- [ ] Repo **About** website → demo URL or landing root
