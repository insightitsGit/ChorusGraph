# ChorusGraph marketing site

Static Hormozi-style landing pages for ChorusGraph. Deploy to GitHub Pages, Netlify, or any static host.

## Pages

| Path | Purpose |
|------|---------|
| `index.html` | Landing — Pain → Proof → Plan |
| `demo.html` | **Try-it playground** — run Cache / ReAct / Plan / Reflection / multi-agent / warm / Cortex in the browser |
| `plugins/prismrag.html` | PrismRAG plug-in story |
| `pricing.html` | 3-tier pricing |
| `benchmarks.html` | Verified results + repro command |

The demo’s step 5 toggles **cache miss vs hit**; step 6 toggles **warm chunks vs PrismCortex**; step 7 has tabs for every use case. Matching offline CLI: `chorusgraph-use-cases` / `cache` / `warm_chunks` / `cortex`.

## Local preview

```bash
cd website
python -m http.server 8080
# Open http://localhost:8080
```

## GitHub Pages

Deployed automatically via [`.github/workflows/pages.yml`](../.github/workflows/pages.yml) on push to `master`.

**Live URLs** (after first deploy):

- Site root: `https://insightitsGit.github.io/ChorusGraph/`
- Interactive demo: `https://insightitsGit.github.io/ChorusGraph/demo.html` ← paste into Product Hunt

Manual setup (if needed): repo **Settings → Pages → Build and deployment → GitHub Actions**.

## Video script

60-second hero/ad script: see `handoffs/handoffProductLanding.md` §2.5. Source narrative for NotebookLM: `docs/NOTEBOOKLM_STORY.md`.

## CTA tracking

Primary CTA links include `utm_source`, `utm_medium`, and `utm_campaign` query params for week-one click measurement.
