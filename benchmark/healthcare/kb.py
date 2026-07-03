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
        "id": "htn_ace_k",
        "topic": "hypertension",
        "text": "ACE inhibitors and MRAs (e.g. spironolactone) increase hyperkalemia risk. Monitor potassium within 1 week of MRA initiation.",
        "source": "ACC/AHA HF",
    },
    {
        "id": "dm_metformin",
        "topic": "diabetes",
        "text": "Type 2 diabetes first-line: metformin unless contraindicated (eGFR <30, metabolic acidosis risk).",
        "source": "ADA Standards 2024",
    },
    {
        "id": "dm_contrast_hold",
        "topic": "diabetes",
        "text": "Hold metformin after iodinated IV contrast when eGFR 30-60 or AKI risk; restart after 48h if renal function stable.",
        "source": "ADA Standards 2024",
    },
    {
        "id": "dm_sulfonylurea_alcohol",
        "topic": "diabetes",
        "text": "Sulfonylureas (glipizide) increase hypoglycemia risk, worsened by alcohol. Counsel on evening alcohol and hypoglycemia signs.",
        "source": "ADA Standards 2024",
    },
    {
        "id": "warfarin_bleed",
        "topic": "anticoagulation",
        "text": "Warfarin increases bleeding risk; monitor INR 2-3 for AF. Avoid NSAIDs and high-dose aspirin without gastroprotection.",
        "source": "CHEST Antithrombotic",
    },
    {
        "id": "doac_procedure",
        "topic": "anticoagulation",
        "text": "For DOACs (apixaban) before high bleeding-risk procedures: hold 48-72h based on renal function; bridging usually not required.",
        "source": "ACCP Perioperative",
    },
    {
        "id": "warfarin_amiodarone",
        "topic": "anticoagulation",
        "text": "Amiodarone inhibits warfarin metabolism — expect INR rise. Reduce warfarin dose ~30-50% and recheck INR within 1 week.",
        "source": "Lexicomp Interaction",
    },
    {
        "id": "statin_primary",
        "topic": "lipids",
        "text": "Moderate-intensity statin for primary prevention when 10-year ASCVD risk ≥7.5%.",
        "source": "ACC/AHA Cholesterol",
    },
    {
        "id": "statin_macrolide",
        "topic": "lipids",
        "text": "CYP3A4 inhibitors (clarithromycin) raise simvastatin levels — avoid combination or hold statin; rhabdomyolysis risk.",
        "source": "FDA Statin Safety",
    },
    {
        "id": "hf_sglt2",
        "topic": "heart_failure",
        "text": "SGLT2 inhibitors (empagliflozin) reduce HF hospitalization in HFrEF regardless of diabetes; use cautiously if eGFR ≥20.",
        "source": "ACC/AHA HF 2022",
    },
    {
        "id": "ace_pregnancy",
        "topic": "pregnancy",
        "text": "ACE inhibitors and ARBs are contraindicated in pregnancy (2nd/3rd trimester teratogenicity). Switch to labetalol, nifedipine, or methyldopa.",
        "source": "ACOG HTN in Pregnancy",
    },
    {
        "id": "ssri_maoi",
        "topic": "psychiatry",
        "text": "Never combine SSRIs with MAOIs — serotonin syndrome risk. Fluoxetine requires ≥5 week washout before MAOI.",
        "source": "APA Depression Guidelines",
    },
    {
        "id": "ckd_nsaid",
        "topic": "nephrology",
        "text": "Avoid NSAIDs (ibuprofen) in CKD stage 4-5 — accelerates renal decline. Prefer acetaminophen, topical agents, or low-dose opioids short-term.",
        "source": "KDIGO CKD",
    },
    {
        "id": "asthma_beta_blocker",
        "topic": "pulmonology",
        "text": "Non-selective beta blockers may worsen bronchospasm in asthma. If required for HF, prefer cardioselective agents with monitoring.",
        "source": "GINA Asthma",
    },
    {
        "id": "copd_steroid",
        "topic": "pulmonology",
        "text": "Systemic corticosteroids for COPD exacerbation (worsening dyspnea, increased sputum). Uncomplicated acute bronchitis without COPD rarely needs steroids.",
        "source": "GOLD COPD",
    },
    {
        "id": "strep_pcn_allergy",
        "topic": "infectious_disease",
        "text": "Strep pharyngitis with non-anaphylactic penicillin allergy: use cephalexin if tolerated, else azithromycin or clindamycin.",
        "source": "IDSA Strep Guidelines",
    },
    {
        "id": "abstain_ungrounded",
        "topic": "safety",
        "text": "If no supporting guideline or interaction data exists for the patient scenario, abstain rather than speculate.",
        "source": "Internal safety policy",
    },
    {
        "id": "abstain_pediatric_dose",
        "topic": "safety",
        "text": "Do not compute weight-based pediatric doses without verified formulary references — abstain and escalate to pharmacist.",
        "source": "Internal safety policy",
    },
    {
        "id": "abstain_unproven_therapy",
        "topic": "safety",
        "text": "Unapproved or unproven therapies (herbal protocols, lunar dosing, off-label chemo without evidence) require abstention.",
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
    ("fluoxetine", "phenelzine"): {
        "severity": "major",
        "mechanism": "serotonin syndrome — MAOI + SSRI",
        "recommendation": "Contraindicated. Washout fluoxetine ≥5 weeks before MAOI.",
    },
    ("warfarin", "amiodarone"): {
        "severity": "major",
        "mechanism": "CYP2C9 inhibition increases warfarin effect",
        "recommendation": "Reduce warfarin dose ~30-50%; recheck INR in 1 week.",
    },
    ("glipizide", "alcohol"): {
        "severity": "moderate",
        "mechanism": "impaired gluconeogenesis + sulfonylurea effect",
        "recommendation": "Counsel on alcohol timing; consider dose reduction or switch.",
    },
    ("metoprolol", "albuterol"): {
        "severity": "moderate",
        "mechanism": "beta-2 antagonism may reduce bronchodilator effect",
        "recommendation": "Use cardioselective beta blocker if needed; monitor wheeze.",
    },
    ("lisinopril", "empagliflozin"): {
        "severity": "minor",
        "mechanism": "additive BP lowering; initial eGFR dip with SGLT2i",
        "recommendation": "Monitor BP and renal function after SGLT2i start.",
    },
}
