# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |
| < 1.0   | No        |

Security fixes are applied on the `master` branch and released per
[`RELEASE.md`](RELEASE.md) / [`CHANGELOG.md`](CHANGELOG.md).

## Reporting a vulnerability

**Please do not open public GitHub issues for security vulnerabilities.**

Use one of these channels:

1. **Preferred — GitHub private security advisory**  
   [Create a private vulnerability report](https://github.com/insightitsGit/ChorusGraph/security/advisories/new)

2. **Alternative — labeled issue (non-sensitive reports only)**  
   If the concern is a hardening suggestion with no active exploit path, you may
   open a public issue with the `security` label. For anything that could expose
   users or tenants, use the private advisory flow above.

Include as much detail as possible:

- Affected version(s) and install path (`pip install chorusgraph`, Docker image,
  k8s manifest, etc.)
- Component (cache gate, tool sandbox, transport, persistence, retrieval,
  multi-tenant isolation, etc.)
- Steps to reproduce or a proof-of-concept
- Impact assessment (confidentiality, integrity, availability, tenant crossover)
- Suggested fix, if you have one

We will acknowledge receipt within **5 business days** and aim to provide an
initial assessment within **10 business days**. Timelines may vary for complex
reports.

## What we consider in scope

- Remote code execution or sandbox escape via tool/MCP execution paths
- Authentication or authorization bypass (federation, API keys, tenant guards)
- Cross-tenant data leakage (cache, memory, retrieval, persistence, ledger)
- Cache poisoning or semantic-cache false-hit attacks with security impact
- PII handling failures in ledger or persistence (`chorusgraph/security/pii.py`)
- TLS/transport misconfiguration defaults
- Dependency vulnerabilities with exploitable paths in ChorusGraph

## Out of scope (please use public issues instead)

- General feature requests
- Benchmark score disputes
- Missing external penetration test / SOC2 (tracked in
  [`docs/ENTERPRISE_READINESS.md`](docs/ENTERPRISE_READINESS.md) Phase 2)
- Vulnerabilities in optional baseline-only dependencies (`langgraph`) unless
  they affect FC/HC native paths

## Security controls in this repository

CI runs on every push to `master` / `main` / `P1_*`:

| Control | Location |
|---------|----------|
| Unit + integration tests (deterministic tier) | `.github/workflows/ci.yml` → `quality` |
| Ruff lint/format | `quality` job |
| Bandit SAST | `security` job |
| pip-audit SCA | `security` job |
| Gitleaks secrets scan | `security` job |

Runtime hardening (tool sandbox, PII redaction, cache isolation, TLS defaults)
is documented in [`docs/ENTERPRISE_READINESS.md`](docs/ENTERPRISE_READINESS.md)
and the design threat model. **External security audit is Phase 2** — built-in
controls are not a substitute for independent review in regulated deployments.

## Safe disclosure

We support coordinated disclosure. We ask that you:

- Give us reasonable time to investigate and patch before public disclosure
- Avoid accessing, modifying, or deleting data that is not yours
- Avoid denial-of-service testing against production systems without prior
  written agreement

We will credit reporters in the advisory or release notes when requested and when
disclosure is complete.

## Security-related configuration

- Never commit `.env`, API keys, license files, or customer data
- Use `CHORUSGRAPH_DETERMINISTIC=1` in CI and local test runs when no live keys
  are needed
- For production deploy guidance, see [`docs/DEPLOY.md`](docs/DEPLOY.md)
