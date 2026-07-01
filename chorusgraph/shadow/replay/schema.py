"""Query-log ingest schema for production shadow replay."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TurnRecord(BaseModel):
    """One hub turn from JSONL export (website_chat_turns)."""

    query: str
    category_slug: str
    response: Any
    timestamp: datetime
    section_id: Optional[str] = None

    @classmethod
    def from_json(cls, data: dict) -> "TurnRecord":
        ts = data["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return cls(
            query=data["query"],
            category_slug=data.get("category_slug") or "general",
            response=data["response"],
            timestamp=ts,
            section_id=data.get("section_id"),
        )
