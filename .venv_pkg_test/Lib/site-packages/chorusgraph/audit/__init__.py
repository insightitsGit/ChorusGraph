"""Cold audit CLI — estimate cache hit rate from historical query logs."""

from chorusgraph.audit.simulate import AuditResult, run_cold_audit

__all__ = ["AuditResult", "run_cold_audit"]
