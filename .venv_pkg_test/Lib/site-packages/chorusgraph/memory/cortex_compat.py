"""Compatibility patches for prismcortex Gemini extraction (ChorusGraph-side)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_PATCHED = False


def _coerce_gist_payload(data: dict) -> dict:
    """Gemini sometimes returns notes: null; ExtractedGist requires str."""
    out = dict(data)
    if out.get("notes") is None:
        out["notes"] = ""
    return out


def apply_cortex_compat_patches() -> None:
    """Patch prismcortex GeminiClient.extract to tolerate null notes from Gemini."""
    global _PATCHED
    if _PATCHED:
        return

    from prismcortex.llm.gemini import (
        GeminiClient,
        _EXTRACT_INSTRUCTIONS,
        _loads_loose,
        _sanitize_user_text,
    )
    from prismcortex.models import ExtractedGist

    def extract(self, text: str, context) -> ExtractedGist:
        ctx = ", ".join(sorted({n.label for n in context.nodes})) or "(none)"
        safe = _sanitize_user_text(text)
        prompt = (
            f"{_EXTRACT_INSTRUCTIONS}\n\nEXISTING CONTEXT: {ctx}\n\n"
            f"--- USER PAYLOAD START ---\n{safe}\n--- USER PAYLOAD END ---"
        )
        raw = self._generate(prompt, json_mode=True)
        try:
            return ExtractedGist.model_validate_json(raw)
        except Exception:
            data = _loads_loose(raw)
            if data is None:
                raise ValueError(f"Extractor returned non-JSON: {raw[:200]!r}") from None
            return ExtractedGist.model_validate(_coerce_gist_payload(data))

    GeminiClient.extract = extract  # type: ignore[method-assign]
    _PATCHED = True
    logger.debug("Applied cortex compat patch: ExtractedGist notes=null coercion")
