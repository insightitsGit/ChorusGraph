"""Multi-agent role graph — Researcher / Writer / Validator on Resonance bus."""

from __future__ import annotations

from chorusgraph.core import END, Graph, START
from chorusgraph.core.node import NodeContext
from chorusgraph.core.channels import NodeUpdate
from chorusgraph.nodes.roles import ResearcherNode, ValidatorNode, WriterNode

TENANT_ID = "multi-agent-demo"
GRAPH_ID = "researcher-writer-validator"


def build_multi_agent_graph():
    def researcher(ctx: NodeContext) -> NodeUpdate:
        msg = ctx.read().get("message") or ""
        plan = f"Research plan for: {msg[:80]}"
        return ctx.publish(
            artifact={"research_plan": plan, "needs_tool": False, "raw_output": plan},
            category_slug="researcher",
            rule_chain=["role=researcher", "plan=deterministic"],
        )

    def writer(ctx: NodeContext) -> NodeUpdate:
        plan = ctx.read().get("research_plan") or ""
        draft = f"Draft based on plan: {plan[:120]}"
        return ctx.publish(
            artifact={"draft_response": draft, "response": draft, "raw_output": draft},
            category_slug="writer",
            rule_chain=["role=writer"],
        )

    def validator(ctx: NodeContext) -> NodeUpdate:
        draft = ctx.read().get("draft_response") or ctx.read().get("response") or ""
        validation = {"ok": bool(draft), "notes": "deterministic validation"}
        return ctx.publish(
            artifact={"validation": validation, "raw_output": str(validation)},
            category_slug="validator",
            rule_chain=["role=validator", f"ok={validation['ok']}"],
        )

    g = Graph(tenant_id=TENANT_ID, graph_id=GRAPH_ID)
    g.add_role_node("researcher", ResearcherNode(), researcher)
    g.add_role_node("writer", WriterNode(), writer)
    g.add_role_node("validator", ValidatorNode(), validator)

    g.add_edge(START, "researcher")
    g.add_edge("researcher", "writer")
    g.add_edge("writer", "validator")
    g.add_edge("validator", END)
    return g.compile()


__all__ = ["GRAPH_ID", "TENANT_ID", "build_multi_agent_graph"]
