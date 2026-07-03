"""CacheProfile profiler — measure keying, ttl, scope from recorded fixtures (H21 T6)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from chorusgraph.sections.models import CacheProfile

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "profiler"


def _normalize_answer(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _answers_match(a: str, b: str) -> bool:
    na, nb = _normalize_answer(a), _normalize_answer(b)
    if na == nb:
        return True
    return na in nb or nb in na


@dataclass
class ProbeEvidence:
    paraphrase_match_rate: float
    delta_flip_rate: float
    recommended_keying: str
    fingerprint_fields: List[str] = field(default_factory=list)
    volatility_half_life_hours: Optional[float] = None
    recommended_ttl_s: Optional[int] = None
    context_sensitive: bool = False
    recommended_scope: str = "global"
    recommended_risk_tier: str = "low"
    raw: Dict[str, Any] = field(default_factory=dict)


def load_fixture(category_slug: str, *, fixtures_dir: Path = FIXTURES_DIR) -> Dict[str, Any]:
    path = fixtures_dir / f"{category_slug}_probe.json"
    if not path.exists():
        raise FileNotFoundError(f"No profiler fixture: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def sensitivity_probe(data: Dict[str, Any]) -> Dict[str, Any]:
    canonical = _normalize_answer(data.get("canonical_answer") or "")
    paraphrases = [p for p in data.get("probes") or [] if p.get("kind") == "paraphrase"]
    deltas = [p for p in data.get("probes") or [] if p.get("kind") == "delta"]
    close_deltas = [p for p in deltas if p.get("semantic_close", True)]

    para_hits = sum(1 for p in paraphrases if _answers_match(p.get("answer", ""), canonical))
    para_rate = para_hits / len(paraphrases) if paraphrases else 1.0

    close_flips = sum(
        1 for p in close_deltas if not _answers_match(p.get("answer", ""), canonical)
    )
    close_flip_rate = close_flips / len(close_deltas) if close_deltas else 0.0

    if close_flip_rate >= 0.5 and para_rate >= 0.5:
        keying = "fingerprint"
        fields = ["drugs", "topic", "labs", "pipeline_depth"]
    elif para_rate >= 0.8 and close_flip_rate < 0.5:
        keying = "semantic"
        fields = []
    else:
        keying = "exact"
        fields = []

    return {
        "paraphrase_match_rate": round(para_rate, 3),
        "delta_flip_rate": round(close_flip_rate, 3),
        "recommended_keying": keying,
        "fingerprint_fields": fields,
    }


def volatility_probe(data: Dict[str, Any]) -> Dict[str, Any]:
    series = list(data.get("volatility_series") or [])
    if len(series) < 2:
        return {"volatility_half_life_hours": None, "recommended_ttl_s": None}

    canonical = _normalize_answer(series[0].get("answer") or "")
    first_change_idx = None
    for i, row in enumerate(series[1:], start=1):
        if not _answers_match(row.get("answer", ""), canonical):
            first_change_idx = i
            break

    if first_change_idx is None:
        return {"volatility_half_life_hours": None, "recommended_ttl_s": None}

    t0 = datetime.fromisoformat(series[0]["timestamp"].replace("Z", "+00:00"))
    t1 = datetime.fromisoformat(series[first_change_idx]["timestamp"].replace("Z", "+00:00"))
    hours = max((t1 - t0).total_seconds() / 3600.0, 1.0)
    ttl_s = int(hours * 3600)
    return {
        "volatility_half_life_hours": round(hours, 2),
        "recommended_ttl_s": ttl_s,
    }


def context_probe(data: Dict[str, Any]) -> Dict[str, Any]:
    probes = list(data.get("context_probes") or [])
    if len(probes) < 2:
        return {"context_sensitive": False, "recommended_scope": "global"}

    answers = [_normalize_answer(p.get("answer", "")) for p in probes]
    unique = len(set(answers))
    sensitive = unique > 1
    scopes = [str(p.get("scope") or "") for p in probes]
    if sensitive and any(s.startswith("session:") or s.startswith("user:") for s in scopes):
        scope = "session" if any(s.startswith("session:") for s in scopes) else "user"
    elif sensitive:
        scope = "tenant"
    else:
        scope = "global"
    return {"context_sensitive": sensitive, "recommended_scope": scope}


def profile_from_fixture(
    category_slug: str,
    *,
    fixtures_dir: Path = FIXTURES_DIR,
) -> tuple[CacheProfile, ProbeEvidence]:
    data = load_fixture(category_slug, fixtures_dir=fixtures_dir)
    sens = sensitivity_probe(data)
    vol = volatility_probe(data)
    ctx = context_probe(data)

    risk = "high" if sens["recommended_keying"] == "fingerprint" else "low"
    profile = CacheProfile(
        keying=sens["recommended_keying"],
        ttl_s=vol.get("recommended_ttl_s"),
        scope=ctx["recommended_scope"],
        risk_tier=risk,
    )
    evidence = ProbeEvidence(
        paraphrase_match_rate=sens["paraphrase_match_rate"],
        delta_flip_rate=sens["delta_flip_rate"],
        recommended_keying=sens["recommended_keying"],
        fingerprint_fields=sens["fingerprint_fields"],
        volatility_half_life_hours=vol.get("volatility_half_life_hours"),
        recommended_ttl_s=vol.get("recommended_ttl_s"),
        context_sensitive=ctx["context_sensitive"],
        recommended_scope=ctx["recommended_scope"],
        recommended_risk_tier=risk,
        raw={"sensitivity": sens, "volatility": vol, "context": ctx, "fixture": category_slug},
    )
    return profile, evidence


def run_profiler(
    category_slugs: List[str],
    *,
    run_id: str,
    fixtures_dir: Path = FIXTURES_DIR,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    output_dir = output_dir or (Path("benchmark/results/profiler") / run_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    profiles: Dict[str, Dict[str, Any]] = {}
    evidence_files: List[str] = []

    for slug in category_slugs:
        profile, evidence = profile_from_fixture(slug, fixtures_dir=fixtures_dir)
        profiles[slug] = profile.model_dump()
        ev_path = output_dir / f"{slug}_evidence.json"
        ev_path.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "category_slug": slug,
                    "profile": profile.model_dump(),
                    "evidence": {
                        "paraphrase_match_rate": evidence.paraphrase_match_rate,
                        "delta_flip_rate": evidence.delta_flip_rate,
                        "recommended_keying": evidence.recommended_keying,
                        "fingerprint_fields": evidence.fingerprint_fields,
                        "volatility_half_life_hours": evidence.volatility_half_life_hours,
                        "recommended_ttl_s": evidence.recommended_ttl_s,
                        "context_sensitive": evidence.context_sensitive,
                        "recommended_scope": evidence.recommended_scope,
                        "recommended_risk_tier": evidence.recommended_risk_tier,
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        evidence_files.append(str(ev_path))

    manifest = {
        "run_id": run_id,
        "profiles": profiles,
        "evidence_files": evidence_files,
        "fixture_dir": str(fixtures_dir),
    }
    manifest_path = output_dir / "profiler_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


__all__ = [
    "FIXTURES_DIR",
    "ProbeEvidence",
    "context_probe",
    "load_fixture",
    "profile_from_fixture",
    "run_profiler",
    "sensitivity_probe",
    "volatility_probe",
]
