"""Internal transforms — ONNX + deterministic CPU, not LLM."""

from chorusgraph.transforms.projector import project_text
from chorusgraph.transforms.templates import (
    format_evidence_block,
    template_fx_response,
    template_multi_fx_response,
    try_template_draft,
)

__all__ = [
    "format_evidence_block",
    "project_text",
    "template_fx_response",
    "template_multi_fx_response",
    "try_template_draft",
]
