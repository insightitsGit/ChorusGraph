"""Clinical guideline snippets for healthcare benchmark retrieval."""

from __future__ import annotations

GUIDELINES: list[dict] = [
    {
        "id": "htn_stage1",
        "topic": "hypertension",
        "text": "Stage 1 hypertension: BP 130-139/80-89. Lifestyle modification first; consider antihypertensive if ASCVD risk ≥10%.",
        "source": "ACC/AHA 2017",
    },
    {
        "id": "htn_stage2",
        "topic": "hypertension",
        "text": "Stage 2 hypertension: BP ≥140/90. Initiate two-drug therapy (ACEi/ARB + CCB or thiazide) plus lifestyle changes.",
        "source": "ACC/AHA 2017",
    },
    {
        "id": "dm_metformin",
        "topic": "diabetes",
        "text": "Type 2 diabetes first-line: metformin unless contraindicated (eGFR <30, metabolic acidosis risk).",
        "source": "ADA Standards 2024",
    },
    {
        "id": "warfarin_bleed",
        "topic": "anticoagulation",
        "text": "Warfarin increases bleeding risk; monitor INR 2-3 for AF. Avoid NSAIDs and high-dose aspirin without gastroprotection.",
        "source": "CHEST Antithrombotic",
    },
    {
        "id": "statin_primary",
        "topic": "lipids",
        "text": "Moderate-intensity statin for primary prevention when 10-year ASCVD risk ≥7.5%.",
        "source": "ACC/AHA Cholesterol",
    },
    {
        "id": "abstain_ungrounded",
        "topic": "safety",
        "text": "If no supporting guideline or interaction data exists for the patient scenario, abstain rather than speculate.",
        "source": "Internal safety policy",
    },
]

DRUG_INTERACTIONS: dict[tuple[str, str], dict] = {
    ("warfarin", "aspirin"): {
        "severity": "major",
        "mechanism": "additive antiplatelet/anticoagulant effect",
        "recommendation": "Avoid combination unless specialist oversight; high bleeding risk.",
    },
    ("metformin", "contrast_iv"): {
        "severity": "major",
        "mechanism": "lactic acidosis risk with iodinated contrast",
        "recommendation": "Hold metformin 48h after contrast; verify renal function.",
    },
    ("lisinopril", "spironolactone"): {
        "severity": "moderate",
        "mechanism": "hyperkalemia risk",
        "recommendation": "Monitor potassium within 1 week of initiation.",
    },
    ("simvastatin", "clarithromycin"): {
        "severity": "major",
        "mechanism": "CYP3A4 inhibition raises statin levels",
        "recommendation": "Avoid or use alternative antibiotic; rhabdomyolysis risk.",
    },
}
