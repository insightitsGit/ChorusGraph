"""Tests for prismcortex Gemini extract compat patch."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from chorusgraph.memory.cortex_compat import _coerce_gist_payload, apply_cortex_compat_patches
from prismcortex.models import ExtractedGist, Subgraph


def test_coerce_gist_payload_null_notes():
    data = _coerce_gist_payload({"entities": [], "relations": [], "notes": None})
    gist = ExtractedGist.model_validate(data)
    assert gist.notes == ""


def test_patched_extract_tolerates_null_notes():
    apply_cortex_compat_patches()
    from prismcortex.llm.gemini import GeminiClient

    client = GeminiClient.__new__(GeminiClient)
    with patch.object(client, "_generate", return_value='{"entities":[],"relations":[],"notes":null}'):
        gist = client.extract("user prefers conservative investing", Subgraph())
    assert gist.notes == ""
