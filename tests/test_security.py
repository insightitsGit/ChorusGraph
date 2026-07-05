"""E3 security — sandbox, auth, cache isolation, PII."""

from __future__ import annotations

import json

import pytest

from chorusgraph.ledger.models import LedgerStep, RouteLedger
from chorusgraph.ledger.sink import SqliteLedgerSink
from chorusgraph.nodes.tool import ToolRegistry, ToolSpec
from chorusgraph.security import (
    AuthorizationError,
    CacheSecurityError,
    CacheSecurityGuard,
    FederationAuthContext,
    ToolAllowlist,
    ToolSecurityError,
    TransportSecurityError,
    TransportSecurityPolicy,
    redact_text,
)
from chorusgraph.transport.prismapi import PrismAPISpine


def test_malicious_tool_arg_blocked():
    registry = ToolRegistry()
    with pytest.raises(ToolSecurityError):
        registry.run(
            "fetch_exchange_rate",
            from_currency="USD; rm -rf /",
            to_currency="EUR",
        )


def test_disallowed_tool_not_registered():
    allow = ToolAllowlist(allowed_tools=frozenset({"safe_only"}))
    registry = ToolRegistry(allowlist=allow)
    with pytest.raises(ToolSecurityError):
        registry.register(ToolSpec(name="evil", description="", parameters={}, fn=lambda: None))


def test_tls_default_blocks_plain_http():
    policy = TransportSecurityPolicy()
    with pytest.raises(TransportSecurityError):
        policy.validate_endpoint("http://api.example.com/data")


def test_chorus_cipher_off_by_default():
    policy = TransportSecurityPolicy.from_env()
    assert policy.effective_cipher_mode() == "tls"


def test_federation_cross_tenant_denied():
    auth = FederationAuthContext(caller_tenant_id="tenant-a", bearer_token="tok")
    spine = PrismAPISpine(tenant_id="tenant-b", auth_context=auth)
    with pytest.raises(AuthorizationError):
        spine.invoke(provider_id="p1", query_text="secret")


def test_federation_missing_token_denied():
    auth = FederationAuthContext(caller_tenant_id="tenant-a", bearer_token=None)
    spine = PrismAPISpine(tenant_id="tenant-a", auth_context=auth)
    with pytest.raises(AuthorizationError):
        spine.invoke(provider_id="p1", query_text="q")


def test_cache_cross_tenant_write_blocked():
    guard = CacheSecurityGuard(tenant_id="tenant-a")
    with pytest.raises(CacheSecurityError):
        guard.authorize_write(
            writer="cache_gate",
            entry_tenant_id="tenant-b",
            provenance={"run_id": "r1"},
        )


def test_cache_user_generated_blocked():
    guard = CacheSecurityGuard(tenant_id="tenant-a")
    with pytest.raises(CacheSecurityError):
        guard.authorize_write(
            writer="cache_gate",
            entry_tenant_id="tenant-a",
            provenance={"run_id": "r1"},
            user_generated=True,
        )


def test_pii_redaction_in_ledger_persist():
    sink = SqliteLedgerSink(":memory:")
    ledger = RouteLedger(
        tenant_id="t1",
        graph_id="g1",
        steps=[
            LedgerStep(
                node="writer",
                rule_chain=["contact=user@example.com", "phone=555-123-4567"],
            )
        ],
    )
    sink.write(ledger)
    stored = sink.get_run(ledger.run_id)
    assert stored is not None
    chain = json.dumps(stored.steps[0].rule_chain)
    assert "user@example.com" not in chain
    assert "555-123-4567" not in chain
    assert "[REDACTED]" in chain


def test_redact_text_email():
    assert "[REDACTED]" in redact_text("reach me at alice@corp.com please")
