# Product Hunt — interactive demo

**Canonical demo URL:** https://insightitsGit.github.io/ChorusGraph/demo.html

Paste this into Product Hunt → **Interactive demo (optional)**.

## What it shows (6 steps)

1. Problem — token burn, audit gap, integration tax  
2. `pip install chorusgraph`  
3. `chorusgraph-demo` — native routing, no API key  
4. Route Ledger — per-hop `rule_chain`  
5. `chorusgraph-audit` — offline cache simulation  
6. Verified benchmarks + GitHub CTAs  

## Run locally

```bash
cd website
python -m http.server 8080
# http://localhost:8080/demo.html
```

## Optional polish

Record the same flow in [Supademo](https://supademo.com/) or [Arcade](https://arcade.software/) (free for PH launches) and embed via iframe on `website/demo.html` if you want hotspot-style interaction.

## Product Hunt checklist

- [ ] Interactive demo URL → `https://insightitsGit.github.io/ChorusGraph/demo.html`
- [ ] Primary CTA → GitHub repo or `pip install chorusgraph`
- [ ] README links to demo (done on `master`)
- [ ] Repo **About** website → demo URL or landing root
