"""Deterministic stub Gemini for offline A/B when live API quota is exhausted."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from benchmark.shared.instrumented_gemini import LlmUsage


class StubGeminiClient:
    """FX-aware stub — exercises graph paths without live Gemini quota."""

    def __init__(self, model_name: str | None = None) -> None:
        _ = model_name
        self.usage = LlmUsage()
        self._step = 0

    def reset_usage(self) -> None:
        self.usage.reset()
        self._step = 0

    def _record(self, text: str) -> None:
        self.usage.record(prompt_tokens=max(len(text) // 4, 8), output_tokens=max(len(text) // 4, 8))

    def _infer_pair(self, text: str) -> tuple[str, str]:
        upper = text.upper()
        codes = re.findall(r"\b(USD|EUR|GBP|JPY|CHF|CAD|AUD)\b", upper)
        if len(codes) >= 2:
            return codes[0], codes[1]
        if "USD" in upper:
            return "USD", "EUR"
        return "EUR", "GBP"

    def generate(self, system: str, user: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        _ = system, history
        self._record(user)
        if "Rewrite" in user or "exact tool rate" in user:
            m = re.search(r"['\"]rate['\"]\s*:\s*([\d.]+)", user)
            rate = m.group(1) if m else "0.8500"
            return f"The exchange rate is 1 USD = {rate} EUR based on authoritative tool data."
        return "Stub writer response with rate 0.9123 for the requested currency pair."

    def generate_json(self, system: str, user: str) -> str:
        _ = system
        self._record(user)
        self._step += 1
        from_c, to_c = self._infer_pair(user)
        if "Observation:" in user or self._step > 1:
            payload = {
                "thought": "Have tool observation; finishing.",
                "action": None,
                "finish": True,
            }
        else:
            payload = {
                "thought": f"Need live {from_c}/{to_c} rate from Frankfurter.",
                "action": {
                    "tool": "fetch_exchange_rate",
                    "args": {"from_currency": from_c, "to_currency": to_c},
                },
                "finish": False,
            }
        return json.dumps(payload)
