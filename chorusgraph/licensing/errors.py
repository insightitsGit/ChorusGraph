"""License validation errors — fail loud for enterprise persistence gates."""


class LicenseError(RuntimeError):
    """Missing, invalid, or insufficient license entitlement."""


class LicenseExpiredError(LicenseError):
    """Signed license file is past expires_at."""
