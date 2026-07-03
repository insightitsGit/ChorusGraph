"""Real Gemini client for finance agent (google.genai — no fake responses)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def resolve_gemini_api_key() -> Optional[str]:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key.strip()
    for candidate in (
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[3] / ".env",
        Path(r"c:\code\InsightitsAIAgent\meeting-scheduler\db_connection.local.env"),
        Path(r"c:\code\InsightitsAIAgent\meeting-scheduler\.env"),
    ):
        if not candidate.exists():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val and val != "CHANGE_ME_GEMINI_KEY":
                    os.environ.setdefault("GEMINI_API_KEY", val)
                    return val
    return None


class GeminiClient:
    """Thin wrapper around google.genai."""

    def __init__(self, model_name: str | None = None) -> None:
        try:
            from google import genai  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "google-genai is not installed. Install with: pip install chorusgraph[gemini]"
            ) from exc
        from google import genai

        api_key = resolve_gemini_api_key()
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not set. Export it or add to .env before running the finance agent."
            )
        resolved = model_name or os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"
        self._model = resolved.split("@", 1)[0]
        self._client = genai.Client(api_key=api_key)

    def _build_prompt(self, system: str, user: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        parts = [f"System:\n{system}\n\nUser:\n{user}"]
        if history:
            hist_text = "\n".join(
                f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in history
            )
            parts.insert(0, f"Conversation so far:\n{hist_text}\n")
        return "\n".join(parts)

    def generate(self, system: str, user: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        from google.genai import types

        prompt = self._build_prompt(system, user, history)
        cfg = types.GenerateContentConfig(temperature=0.2, max_output_tokens=1024)
        response = self._client.models.generate_content(model=self._model, contents=prompt, config=cfg)
        return (response.text or "").strip()

    def generate_stream(self, system: str, user: str, history: Optional[List[Dict[str, str]]] = None):
        """Yield text chunks from the live Gemini stream (real client only)."""
        from google.genai import types

        prompt = self._build_prompt(system, user, history)
        cfg = types.GenerateContentConfig(temperature=0.2, max_output_tokens=1024)
        stream = self._client.models.generate_content_stream(
            model=self._model,
            contents=prompt,
            config=cfg,
        )
        for chunk in stream:
            text = getattr(chunk, "text", None)
            if text:
                yield text

    def generate_json(self, system: str, user: str) -> str:
        from google.genai import types

        prompt = self._build_prompt(system, user)
        cfg = types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=2048,
            response_mime_type="application/json",
        )
        response = self._client.models.generate_content(model=self._model, contents=prompt, config=cfg)
        return (response.text or "").strip()
