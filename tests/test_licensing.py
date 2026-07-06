"""Tests for offline enterprise license validation."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from chorusgraph.licensing import (
    ENTERPRISE_PERSISTENCE,
    LicenseError,
    LicenseExpiredError,
    clear_license_cache,
    require_feature,
    validate_offline_file,
)
from tests.support.license_fixture import sign_license_payload, write_test_license


def test_validate_offline_file_accepts_valid_license(tmp_path, monkeypatch):
    clear_license_cache()
    path = write_test_license(tmp_path / "lic.json", features=[ENTERPRISE_PERSISTENCE])
    payload = validate_offline_file(path)
    assert ENTERPRISE_PERSISTENCE in payload["features"]


def test_validate_offline_rejects_tampered_signature(tmp_path):
    clear_license_cache()
    path = write_test_license(tmp_path / "lic.json", features=[ENTERPRISE_PERSISTENCE])
    data = json.loads(path.read_text())
    data["payload"]["tenant"] = "evil-corp"
    path.write_text(json.dumps(data))
    with pytest.raises(LicenseError, match="signature"):
        validate_offline_file(path)


def test_validate_offline_rejects_expired_license(tmp_path):
    clear_license_cache()
    expires = datetime.now(timezone.utc) - timedelta(days=1)
    payload = {
        "tenant": "expired",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires.isoformat(),
        "features": [ENTERPRISE_PERSISTENCE],
    }
    path = tmp_path / "expired.json"
    path.write_text(json.dumps(sign_license_payload(payload)))
    with pytest.raises(LicenseExpiredError):
        validate_offline_file(path)


def test_require_feature_missing_env(monkeypatch):
    clear_license_cache()
    monkeypatch.delenv("CHORUSGRAPH_LICENSE_FILE", raising=False)
    with pytest.raises(LicenseError, match="CHORUSGRAPH_LICENSE_FILE"):
        require_feature(ENTERPRISE_PERSISTENCE)


def test_require_feature_wrong_entitlement(tmp_path, monkeypatch):
    clear_license_cache()
    path = write_test_license(tmp_path / "lic.json", features=["other_feature"])
    monkeypatch.setenv("CHORUSGRAPH_LICENSE_FILE", str(path))
    with pytest.raises(LicenseError, match="enterprise_persistence"):
        require_feature(ENTERPRISE_PERSISTENCE)


def test_prismrag_feature_does_not_unlock_persistence(tmp_path, monkeypatch):
    clear_license_cache()
    path = write_test_license(tmp_path / "lic.json", features=["prismrag_remap"])
    monkeypatch.setenv("CHORUSGRAPH_LICENSE_FILE", str(path))
    with pytest.raises(LicenseError, match="enterprise_persistence"):
        require_feature(ENTERPRISE_PERSISTENCE)
