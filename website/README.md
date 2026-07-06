# ChorusGraph marketing site

Static Hormozi-style landing pages for ChorusGraph. Deploy to GitHub Pages, Netlify, or any static host.

## Pages

| Path | Purpose |
|------|---------|
| `index.html` | Landing — Pain → Proof → Plan |
| `plugins/prismrag.html` | PrismRAG plug-in story |
| `pricing.html` | 3-tier pricing |
| `benchmarks.html` | Verified results + repro command |

## Local preview

```bash
cd website
python -m http.server 8080
# Open http://localhost:8080
```

## GitHub Pages

Set site source to `/website` folder on `master`, or copy `website/` contents to `docs/` if using docs-based Pages.

## Video script

60-second hero/ad script: see `handoffs/handoffProductLanding.md` §2.5. Source narrative for NotebookLM: `docs/NOTEBOOKLM_STORY.md`.

## CTA tracking

Primary CTA links include `utm_source`, `utm_medium`, and `utm_campaign` query params for week-one click measurement.
