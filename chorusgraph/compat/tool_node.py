"""Tool duck-typing for LangChain-style tools — T8."""

from __future__ import annotations

from typing import Any, Dict


class ToolNode:
    """Invoke anything with ``.invoke`` and ``.name`` — no langchain import."""

    def __init__(self, tools: list[Any]) -> None:
        self.tools = {getattr(t, "name", type(t).__name__): t for t in tools}

    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        call = (state.get("tool_calls") or [{}])[-1]
        name = call.get("name") or call.get("tool")
        tool = self.tools.get(str(name))
        if tool is None:
            raise KeyError(f"Unknown tool: {name!r}")
        result = tool.invoke(call.get("args") or {})
        return {"tool_result": result, "last_tool": name}


__all__ = ["ToolNode"]
