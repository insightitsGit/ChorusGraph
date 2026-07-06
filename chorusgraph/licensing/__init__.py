"""Enterprise feature licensing — offline Ed25519 license files (auditable, no obfuscation)."""

from chorusgraph.licensing.errors import LicenseError, LicenseExpiredError
from chorusgraph.licensing.validator import (
    ENTERPRISE_PERSISTENCE,
    clear_license_cache,
    require_feature,
    validate_offline_file,
)

__all__ = [
    "ENTERPRISE_PERSISTENCE",
    "LicenseError",
    "LicenseExpiredError",
    "clear_license_cache",
    "require_feature",
    "validate_offline_file",
]
