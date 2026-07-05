# PII Retention Policy (E3)

**Effective:** Enterprise track E3 · **Applies to:** Route Ledger, structured logs, cache metadata

## Redaction

Emails, phone numbers, SSN-like patterns, and credit-card-like sequences are replaced with `[REDACTED]` before ledger persistence (`chorusgraph/security/pii.py`).

## Retention

| Store | Default retention | Deletion |
|-------|-------------------|----------|
| Route Ledger (SQLite dev) | 90 days | Manual / E5 forget API |
| Route Ledger (Postgres prod) | Configurable via `CHORUSGRAPH_LEDGER_RETENTION_DAYS` | E5 right-to-forget |
| Application logs | 30 days | Log shipper policy |
| Cortex memory | Until `forget()` | E5 product-wide delete |

## Access

Ledger and logs are tenant-scoped. Cross-tenant access is denied by E3 auth/cache guards and verified in E6 leakage tests.
