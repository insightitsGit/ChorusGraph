"""Gemini client wrapper with per-run LLM call and token accounting."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from benchmark.benchmark_flags import get_flags
from chorusgraph.examples.finance_agent.gemini_client import GeminiClient

# Gemini 2.5 Flash list pricing (USD per 1M tokens) — for cost_usd estimates only.
_INPUT_USD_PER_M = 0.15
_OUTPUT_USD_PER_M = 0.60


@dataclass
class LlmUsage:
    llm_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0

    def record(self, *, prompt_tokens: int, output_tokens: int) -> None:
        self.llm_calls += 1
        self.tokens_in += prompt_tokens
        self.tokens_out += output_tokens

    @property
    def cost_usd(self) -> float:
        return (self.tokens_in * _INPUT_USD_PER_M + self.tokens_out * _OUTPUT_USD_PER_M) / 1_000_000

    def reset(self) -> None:
        self.llm_calls = 0
        self.tokens_in = 0
        self.tokens_out = 0


def _usage_from_response(response: Any) -> tuple[int, int]:
    meta = getattr(response, "usage_metadata", None)
    if meta is not None:
        prompt = int(getattr(meta, "prompt_token_count", 0) or 0)
        output = int(getattr(meta, "candidates_token_count", 0) or 0)
        if prompt or output:
            return prompt, output
    text = (getattr(response, "text", None) or "") or ""
    # Fallback when API omits usage metadata.
    return max(len(text) // 4, 1), max(len(text) // 4, 1)


class InstrumentedGeminiClient:
    """Same Gemini model/settings as finance agent, with usage tracking."""

    def __init__(self, model_name: str | None = None) -> None:
        self._inner = GeminiClient(model_name=model_name)
        self.usage = LlmUsage()
        self._client = self._inner._client
        self.model = self._inner._model

    def reset_usage(self) -> None:
        self.usage.reset()

    def generate(self, system: str, user: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        from google.genai import types

        prompt = self._inner._build_prompt(system, user, history)
        cfg = types.GenerateContentConfig(temperature=get_flags().temperature, max_output_tokens=1024)
        response = self._client.models.generate_content(model=self.model, contents=prompt, config=cfg)
        prompt_t, out_t = _usage_from_response(response)
        self.usage.record(prompt_tokens=prompt_t, output_tokens=out_t)
        return (response.text or "").strip()

    def generate_json(self, system: str, user: str) -> str:
        from google.genai import types

        prompt = self._inner._build_prompt(system, user)
        cfg = types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=2048,
            response_mime_type="application/json",
        )
        response = self._client.models.generate_content(model=self.model, contents=prompt, config=cfg)
        prompt_t, out_t = _usage_from_response(response)
        self.usage.record(prompt_tokens=prompt_t, output_tokens=out_t)
        return (response.text or "").strip()
