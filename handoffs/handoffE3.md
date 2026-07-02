# Handoff E3 — Security (§21 build-out)

**From:** Architect (Claude) · **To:** Senior Engineer (Cursor) · **Director:** Amin
**Design reference:** [`../docs/ENTERPRISE_READINESS.md`](../docs/ENTERPRISE_READINESS.md) **§E3** + **DESIGN §21** (the register) · [`../docs/PROCESS.md`](../docs/PROCESS.md).
**Depends on:** E1, E2. **Return in:** `handoffs/handoffbackE3.md`.

Security is the gate before **any** real customer touches the system. Build the §21 register, don't just re-document it.

## 0. Operating rules
No fakes; recorded fixtures. One bounded increment. Nothing ships as a "security feature" until its ship-gate item is closed.

## 1. Goal
Close the DESIGN §21 ship-gate security items so a regulated buyer can trust the runtime.

## 2. Deliverables (from §21)
- **Tool execution safety** — sandboxing + allowlists + capability scoping (no arbitrary side effects from injected content).
- **Transport** — mTLS/TLS **default**; the homegrown CHORUS cipher **audited, or opt-in-off** (never the default security claim until audited).
- **Federation authn/authz** — mutual auth + per-request authorization on PrismAPI; tenant-scoped.
- **Cache-poisoning controls** — per-tenant cache isolation, write-authorization, entry provenance/signing, never-cache untrusted/user-generated sections.
- **PII** — redaction in ledger/logs; retention policy.
- **CI security** — SAST + SCA (dependency CVEs) + secrets-scanning added to the E1 pipeline; a written **threat model**.

## 3. Out of scope
E1/E2 · E4–E9 · MVP fixes · enabling any item as a security guarantee before its audit/gate.

## 4. Acceptance criteria
- [ ] Tool sandboxing + allowlists enforced; a malicious-tool-arg test is contained.
- [ ] mTLS/TLS is the default transport; cipher is audited or off-by-default (documented).
- [ ] Federated calls require auth + are authorized per request + tenant-scoped; a cross-tenant access attempt is denied.
- [ ] Cache write-auth + per-tenant isolation; a poisoning attempt cannot serve to another tenant.
- [ ] PII redaction verified in logs/ledger; retention policy documented.
- [ ] SAST/SCA/secrets-scan run in CI; **no high/critical** findings unresolved; threat-model doc committed.

## 5. Open questions for handoffbackE3
1. Sandboxing approach (subprocess / container / wasm) and its limits.
2. Crypto path — audit plan, or default-off decision.
3. authz model for federation.
4. Any §21 item that needs to become its own handoff.
5. Proposed E4 scope.

## 6. Return format
Summary · file tree · how to run (incl. the security tests) · CI security-scan result · decisions/deviations · blockers · answers to §5 · proposed E4.

---
*Handoff E3 · enterprise track · §21 security build-out · gate before any real customer.*
