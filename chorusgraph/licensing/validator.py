"""Offline signed license validation — shared pattern for ChorusGraph enterprise gates."""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from chorusgraph.licensing.errors import LicenseError, LicenseExpiredError
from chorusgraph.licensing.keys import license_public_key_bytes

ENTERPRISE_PERSISTENCE = "enterprise_persistence"
PRISMRAG_REMAP = "prismrag_remap"

_ENTERPRISE_CONTACT = "https://github.com/insightitsGit/ChorusGraph/blob/master/docs/ENTERPRISE_READINESS.md"
_CACHED: dict[str, Any] | None = None
_CACHED_PATH: str | None = None


def clear_license_cache() -> None:
    global _CACHED, _CACHED_PATH
    _CACHED = None
    _CACHED_PATH = None


def _canonical_payload_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def validate_offline_file(path: str | Path) -> dict[str, Any]:
    """
    Verify a signed offline license file — zero network calls.

    File format::

        {"payload": {...}, "signature": "<base64 Ed25519 over canonical payload JSON>"}
    """
    global _CACHED, _CACHED_PATH
    resolved = str(Path(path).resolve())
    if _CACHED is not None and _CACHED_PATH == resolved:
        return dict(_CACHED)

    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LicenseError(f"Could not read license file {path!r}: {exc}") from exc

    payload = raw.get("payload")
    signature_b64 = raw.get("signature")
    if not isinstance(payload, dict) or not isinstance(signature_b64, str):
        raise LicenseError("License file must contain 'payload' (object) and 'signature' (string).")

    try:
        signature = base64.b64decode(signature_b64)
        public_key = Ed25519PublicKey.from_public_bytes(license_public_key_bytes())
        public_key.verify(signature, _canonical_payload_bytes(payload))
    except (InvalidSignature, ValueError) as exc:
        raise LicenseError("License signature verification failed — file may be tampered.") from exc

    expires_at = payload.get("expires_at")
    if expires_at:
        try:
            exp = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > exp:
                raise LicenseExpiredError(
                    f"License expired on {exp.date()}. Renew via enterprise contact: {_ENTERPRISE_CONTACT}"
                )
        except LicenseExpiredError:
            raise
        except Exception as exc:
            raise LicenseError(f"Invalid expires_at in license: {expires_at!r}") from exc

    _CACHED = dict(payload)
    _CACHED_PATH = resolved
    return dict(payload)


def _resolve_license_payload() -> dict[str, Any]:
    path = os.environ.get("CHORUSGRAPH_LICENSE_FILE", "").strip()
    if not path:
        raise LicenseError(
            "Enterprise persistence requires a signed offline license file. "
            f"Set CHORUSGRAPH_LICENSE_FILE to the path of your license JSON, or contact Insight IT: "
            f"{_ENTERPRISE_CONTACT}"
        )
    return validate_offline_file(path)


def require_feature(feature: str) -> dict[str, Any]:
    """Raise LicenseError if ``feature`` is not entitled in the active license file."""
    payload = _resolve_license_payload()
    features = payload.get("features") or []
    if not isinstance(features, list):
        raise LicenseError("License payload 'features' must be a list.")
    if feature not in features:
        raise LicenseError(
            f"License does not include feature {feature!r}. "
            f"Entitled features: {sorted(features) or '(none)'}. "
            f"Enterprise contact: {_ENTERPRISE_CONTACT}"
        )
    return payload
