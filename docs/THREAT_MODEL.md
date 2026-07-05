# ChorusGraph Threat Model (E3)

**Version:** 1.0 · **Track:** Enterprise E3 · **Status:** Initial

## Scope

ChorusGraph runtime: native graph engine, tool nodes, PrismAPI federation, cache gate, Route Ledger, Cortex memory adapter.

## Assets

| Asset | Sensitivity | Storage |
|-------|-------------|---------|
| Route Ledger | Audit + possible PII in rule_chain | SQLite/Postgres |
| Cache entries | Tenant business data | PrismCache / Redis |
| Cortex memory | Long-term agent knowledge | SQLite + graph store |
| API keys (Gemini) | Secret | Env / vault |
| Federated retrieval | Cross-tenant KB vectors | CHORUS / HTTP |

## Trust boundaries

1. **User input → tool args** — untrusted; sandboxed via allowlist + injection scan.
2. **Tenant A → Tenant B data** — denied at federation auth + cache guard.
3. **Cross-region transport** — TLS default; CHORUS cipher opt-in only (unaudited).
4. **Logs / ledger persistence** — PII redacted at write.

## STRIDE summary

| Threat | Mitigation (E3) |
|--------|-----------------|
| Spoofing (federation) | Bearer token + tenant match on PrismAPI |
| Tampering (cache poison) | Write-auth, provenance, no user-generated cache |
| Repudiation | Route Ledger (existing) |
| Information disclosure | PII redaction, tenant-scoped cache keys |
| Denial of service | E2 breakers/retries (separate handoff) |
| Elevation (arbitrary tools) | Tool allowlist + arg key scoping |

## Residual risks

- CHORUS homegrown cipher: **not a security claim** until independent audit; off by default.
- In-process tool sandbox: pattern-based, not WASM/subprocess isolation — sufficient for E3 gate, not full RCE containment.
- PII redaction: regex-based; custom formats may leak — extend patterns per deployment.

## CI security gates

- **Bandit** SAST on `chorusgraph/`
- **pip-audit** SCA on locked dependencies
- **Gitleaks** secrets scan (continue-on-error for baseline)

See `.github/workflows/ci.yml` job `security`.
