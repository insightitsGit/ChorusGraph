"""Role-typed node scaffold — composition over inheritance (DESIGN §7.7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

RoleFn = Callable[[Dict[str, Any]], Dict[str, Any]]


@dataclass
class RoleTemplate:
    """Attachable role: prompt, tools, output target."""

    role: str
    system_prompt: str
    allowed_tools: Sequence[str] = field(default_factory=list)
    output_key: str = "draft_response"


@dataclass
class Node:
    """
    Base graph node. Every role variant IS-A Node.

    A plain Node can be promoted via `with_role()`.
    """

    node_id: str
    role: Optional[RoleTemplate] = None
    handler: Optional[RoleFn] = None

    def with_role(self, template: RoleTemplate) -> "Node":
        return Node(node_id=self.node_id, role=template, handler=self.handler)

    def bind(self, handler: RoleFn) -> "Node":
        return Node(node_id=self.node_id, role=self.role, handler=handler)

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if self.handler is None:
            raise RuntimeError(f"Node {self.node_id} has no handler bound")
        return self.handler(state)


def _researcher_template() -> RoleTemplate:
    return RoleTemplate(
        role="researcher",
        system_prompt=(
            "You are a finance research agent. Decide whether live market data or a "
            "deterministic calculation is required. Output structured plan only."
        ),
        allowed_tools=("fetch_exchange_rate", "compound_interest"),
        output_key="research_plan",
    )


def _writer_template() -> RoleTemplate:
    return RoleTemplate(
        role="writer",
        system_prompt=(
            "You are a finance writer. Draft a concise, accurate answer using ONLY "
            "provided tool results and conversation context. Cite numbers exactly."
        ),
        allowed_tools=(),
        output_key="draft_response",
    )


def _validator_template() -> RoleTemplate:
    return RoleTemplate(
        role="validator",
        system_prompt=(
            "You are a finance validator. Check that the draft uses tool data correctly "
            "and does not invent rates or figures."
        ),
        allowed_tools=(),
        output_key="validation",
    )


def ResearcherNode(node_id: str = "researcher") -> Node:
    return Node(node_id=node_id, role=_researcher_template())


def WriterNode(node_id: str = "writer") -> Node:
    return Node(node_id=node_id, role=_writer_template())


def ValidatorNode(node_id: str = "validator") -> Node:
    return Node(node_id=node_id, role=_validator_template())


def promote(node: Node, role: str) -> Node:
    """Promote a plain Node to a role variant."""
    factories = {
        "researcher": _researcher_template,
        "writer": _writer_template,
        "validator": _validator_template,
    }
    if role not in factories:
        raise ValueError(f"Unknown role: {role}")
    return node.with_role(factories[role]())
