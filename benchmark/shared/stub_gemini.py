"""Stub Gemini for offline benchmark graph tests."""

from __future__ import annotations

import json
from typing import Dict, List, Optional

from benchmark.shared.instrumented_gemini import LlmUsage


class StubGemini:
    """Deterministic Gemini stub for graph routing tests (no API)."""

    def __init__(self, react_responses: List[dict], writer_text: str = "The rate is 1.23.") -> None:
        self._react = react_responses
        self._writer_text = writer_text
        self._react_i = 0
        self.usage = LlmUsage()

    def reset_usage(self) -> None:
        self.usage.reset()

    def generate_json(self, _system: str, _user: str) -> str:
        idx = min(self._react_i, len(self._react) - 1)
        self._react_i += 1
        self.usage.record(prompt_tokens=50, output_tokens=30)
        return json.dumps(self._react[idx])

    def generate(self, _system: str, _user: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        self.usage.record(prompt_tokens=40, output_tokens=20)
        return self._writer_text
