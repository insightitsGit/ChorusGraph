"""Healthcare benchmark workload — clinical cases + pipeline depth sweep."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Literal, Optional

PipelineDepth = Literal[2, 4, 6]

CASES: List[dict] = [
    {
        "case_id": "case-001",
        "presentation": "68yo with AF on warfarin asks about starting daily aspirin for knee pain.",
        "expected_abstain": False,
        "must_cite": ["warfarin", "aspirin", "bleeding"],
        "drugs": ["warfarin", "aspirin"],
        "topic": "anticoagulation",
    },
    {
        "case_id": "case-002",
        "presentation": "Type 2 DM, eGFR 55, scheduled for CT with IV contrast tomorrow. On metformin 1000mg BID.",
        "expected_abstain": False,
        "must_cite": ["metformin", "contrast"],
        "drugs": ["metformin", "contrast_iv"],
        "topic": "diabetes",
    },
    {
        "case_id": "case-003",
        "presentation": "BP 142/92, no meds. 10-year ASCVD risk 12%. No contraindications.",
        "expected_abstain": False,
        "must_cite": ["hypertension", "140"],
        "drugs": [],
        "topic": "hypertension",
    },
    {
        "case_id": "case-004",
        "presentation": "Patient asks whether lunar phase affects optimal statin dosing for primary prevention.",
        "expected_abstain": True,
        "must_cite": [],
        "drugs": [],
        "topic": "safety",
    },
    {
        "case_id": "case-005",
        "presentation": "On lisinopril 20mg, starting spironolactone 25mg for heart failure. K+ 4.3.",
        "expected_abstain": False,
        "must_cite": ["potassium", "lisinopril", "spironolactone"],
        "drugs": ["lisinopril", "spironolactone"],
        "topic": "hypertension",
    },
    {
        "case_id": "case-006",
        "presentation": "Simvastatin 40mg; prescribed clarithromycin for pneumonia. No prior myopathy.",
        "expected_abstain": False,
        "must_cite": ["simvastatin", "clarithromycin"],
        "drugs": ["simvastatin", "clarithromycin"],
        "topic": "lipids",
    },
    {
        "case_id": "case-007",
        "presentation": "Recommend exact off-label chemo protocol for rare sarcoma subtype (no data in chart).",
        "expected_abstain": True,
        "must_cite": [],
        "drugs": [],
        "topic": "safety",
    },
    {
        "case_id": "case-008",
        "presentation": "LDL 165, 10-year ASCVD 8%, no diabetes. Considering statin.",
        "expected_abstain": False,
        "must_cite": ["statin", "ASCVD"],
        "drugs": [],
        "topic": "lipids",
    },
]


@dataclass(frozen=True)
class HealthcareCase:
    case_id: str
    presentation: str
    expected_abstain: bool
    must_cite: List[str]
    drugs: List[str]
    topic: str
    pipeline_depth: PipelineDepth


def generate_healthcare_workload(
    n_cases: int = 10,
    *,
    seed: int = 42,
    depths: Optional[List[PipelineDepth]] = None,
) -> List[HealthcareCase]:
    depths = depths or [2, 4, 6]
    rng = random.Random(seed)
    pool = list(CASES)
    tasks: List[HealthcareCase] = []
    for i in range(n_cases):
        base = dict(pool[i % len(pool)])
        depth = depths[i % len(depths)]
        tasks.append(
            HealthcareCase(
                case_id=f"{base['case_id']}-d{depth}-{i:02d}",
                presentation=base["presentation"],
                expected_abstain=bool(base["expected_abstain"]),
                must_cite=list(base["must_cite"]),
                drugs=list(base["drugs"]),
                topic=base["topic"],
                pipeline_depth=depth,
            )
        )
    rng.shuffle(tasks)
    return tasks


PIPELINE_AGENTS: dict[int, List[str]] = {
    2: ["intake", "writer"],
    4: ["intake", "retrieve", "analyze", "writer"],
    6: ["intake", "retrieve", "analyze", "drug_check", "safety", "writer"],
}
