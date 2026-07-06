"""Stub Gemini clients for deterministic CI (E1 — no API keys)."""

from __future__ import annotations

import json

from benchmark.shared.instrumented_gemini import LlmUsage


class DeterministicGeminiStub:
    """Minimal Gemini stand-in — satisfies benchmark + finance agent interfaces."""

    def __init__(self, model_name: str | None = None, *, model: str | None = None) -> None:
        resolved = model_name or model or "deterministic-stub"
        self.usage = LlmUsage()
        self._client = None
        self.model = resolved
        self._model = self.model
        self.model_id = self.model

    def reset_usage(self) -> None:
        self.usage.reset()

    def generate(self, system: str, user: str, history: list[dict[str, str]] | None = None) -> str:
        self.usage.record(prompt_tokens=32, output_tokens=16)
        if "ABSTAIN" in system.upper():
            return "ABSTAIN: insufficient grounded evidence."
        if "writer" in system.lower() or "response" in system.lower():
            return "Based on frankfurter.app (ECB) data, the USD to EUR rate is 0.87352 as of 2026-07-03."
        return "Deterministic stub response for CI."

    def generate_json(self, system: str, user: str) -> str:
        self.usage.record(prompt_tokens=40, output_tokens=24)
        low = f"{system}\n{user}".lower()
        if "safety" in low:
            return json.dumps({"verdict": "APPROVED", "missing_evidence": [], "reason": "stub"})
        if "intake" in low:
            return json.dumps(
                {"facts": "stub case", "drugs": [], "topic": "clinical", "question": user[:80]}
            )
        if "retrieve" in low:
            return json.dumps({"cited_ids": ["guideline-1"], "summary": "Stub guideline summary."})
        if "analyze" in low:
            return json.dumps({"reasoning": "Stub clinical reasoning.", "uncertainties": []})
        if "drug" in low:
            return json.dumps({"interactions": [], "summary": "No interactions."})
        if "react" in low or "tool" in low or "action" in low:
            return json.dumps(
                {
                    "thought": "use tool",
                    "finish": False,
                    "action": {
                        "tool": "fetch_exchange_rate",
                        "args": {"from_currency": "USD", "to_currency": "EUR"},
                    },
                }
            )
        return json.dumps({"thought": "done", "finish": True, "action": None})

    def generate_stream(self, system: str, user: str, history=None):  # noqa: ANN001
        yield self.generate(system, user, history)

    def _generate(self, prompt: str, *, json_mode: bool = False) -> str:
        if json_mode:
            return self.generate_json("", prompt)
        return self.generate("", prompt)

    def extract(self, text: str, context) -> object:
        from prismcortex.models import ExtractedGist

        self.usage.record(prompt_tokens=24, output_tokens=12)
        return ExtractedGist.model_validate(
            {
                "summary": text[:120] or "stub memory",
                "entities": [],
                "relations": [],
                "notes": "",
            }
        )
