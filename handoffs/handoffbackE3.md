# Handoffback E3 — Security

**Status:** Complete on branch `P1_Enterprice1`  
**Depends on:** E1, E2

## Summary

E3 implements §21 security foundations: tool allowlist/sandbox, TLS-default transport policy (CHORUS cipher opt-in off), federation authn/authz, cache write-authorization with tenant isolation, PII redaction at ledger persist, CI SAST/SCA/secrets scan, and threat model documentation.

## How to run

```powershell
pytest tests/test_security.py -v
pytest
bandit -r chorusgraph -ll
pip-audit
```

## Decisions

| Topic | Choice | Why |
|-------|--------|-----|
| Tool sandbox | Allowlist + injection regex scan | No new deps; blocks obvious SSRF/RCE patterns in args |
| CHORUS cipher | **Off by default** (`CHORUSGRAPH_CHORUS_CIPHER=1` to opt in) | DESIGN §21 — no security claim until audit |
| Federation auth | Bearer + server-side tenant match | Blocks cross-tenant PrismAPI invoke |
| Cache poison | `CacheSecurityGuard` write-auth + no user-generated sections | Per-tenant isolation at write time |
| PII | Regex redaction at ledger `write()` | Central enforcement point |

## Proposed E4

Structured JSON logging, OpenTelemetry spans per node, health/readiness endpoints, runbooks.
