"""HC2 prompts — bounded envelope handoffs (not full transcript)."""

from __future__ import annotations

from typing import List

INTAKE_D_SYSTEM = (
    "Clinical intake agent. Return JSON only: "
    '{"facts":"concise clinical facts","drugs":["..."],"topic":"...","question":"..."}'
)

RETRIEVE_D_SYSTEM = (
    "Medical librarian. Summarize hop_input.retrieved_docs for upstream facts. "
    'Return JSON only: {"cited_ids":["doc-id",...],"summary":"max 2 sentences"}'
)

ANALYZE_D_SYSTEM = (
    "Clinical analyst. Reason over upstream intake + retrieve artifacts only. "
    'Return JSON only: {"reasoning":"concise","uncertainties":["..."]}'
)

DRUG_D_SYSTEM = (
    "Interpret hop_input.interactions for upstream.drugs. "
    'Return JSON only: {"interactions":[...],"summary":"one sentence"}'
)

SAFETY_D_SYSTEM = (
    "Safety validator. Review hop_input snapshot: facts, cited_ids, retrieve_summary, "
    "analysis, drug severities. "
    "APPROVED = enough grounded evidence for a recommendation (including recommending AGAINST an action). "
    "ABSTAIN = only when snapshot is empty or wholly insufficient. "
    'Return JSON only: {"verdict":"APPROVED"|"ABSTAIN","missing_evidence":["..."],"reason":"one sentence"}'
)

WRITER_D_SYSTEM = (
    "Clinical writer. Use upstream safety verdict + hop_input facts, cited_ids, drug_summary. "
    "Produce a concise cited recommendation. If upstream.verdict is ABSTAIN, refuse briefly. "
    "When required terms are listed, each must appear verbatim in your answer."
)

WRITER_SHALLOW_D_SYSTEM = (
    "Clinical writer. Use hop_input intake facts only. "
    "Produce a concise initial assessment — no safety hop has run; do not refuse. "
    "When required terms are listed, each must appear verbatim in your answer."
)

WRITER_MID_D_SYSTEM = (
    "Clinical writer. Use upstream intake + retrieve + analyze artifacts. "
    "Produce a concise cited recommendation — no safety hop has run; do not abstain. "
    "When required terms are listed, each must appear verbatim in your answer."
)


def writer_must_cite_block(must_cite: List[str]) -> str:
    if not must_cite:
        return ""
    terms = ", ".join(must_cite)
    return f"\n\nRequired terms (must appear verbatim in your answer): {terms}\n"
