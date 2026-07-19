"""Unified configurable Agent type (DESIGN §7.8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from chorusgraph.agents.policy import (
    BeliefPolicy,
    PATTERN_DEFAULTS,
    PatternOpts,
    PlanPolicy,
    PlanSolveOpts,
    ReActOpts,
    ReflectionOpts,
)
from chorusgraph.agents.strategies import get_strategy
from chorusgraph.agents.strategies.base import AgentContext, AgentRunResult
from chorusgraph.nodes.roles import RoleTemplate
from chorusgraph.nodes.tool import ToolRegistry


@dataclass
class Agent:
    """
    One agent type — pattern selected via pluggable strategy config.

    >>> agent = Agent(pattern="react", tools=registry, model=gemini.generate_json)
    >>> agent.run("Compare USD/EUR and USD/GBP")
    """

    pattern: str
    tools: ToolRegistry
    model: Callable[[str, str], str]
    role: Optional[RoleTemplate] = None
    policy: PlanPolicy = field(default_factory=PlanPolicy)
    pattern_opts: Optional[PatternOpts] = None
    belief: BeliefPolicy = field(default_factory=BeliefPolicy)
    llm_text: Optional[Callable[[str, str], str]] = None

    def __post_init__(self) -> None:
        if self.pattern_opts is None:
            self.pattern_opts = PATTERN_DEFAULTS[self.pattern]  # type: ignore[assignment]

    def with_interceptors(
        self,
        *,
        before_llm: Optional[Callable[..., Any]] = None,
        after_llm: Optional[Callable[..., Any]] = None,
    ) -> "Agent":
        """
        Return a copy whose ``model`` (and ``llm_text``) fire ADR-008 hooks.

        Use when the Agent runs outside ``NodeContext.call_llm`` (AgentNode path).
        """
        from chorusgraph.core.intercept import wrap_llm_callable

        wrapped = wrap_llm_callable(self.model, before_llm=before_llm, after_llm=after_llm)
        text = self.llm_text
        if text is not None and (before_llm or after_llm):
            text = wrap_llm_callable(text, before_llm=before_llm, after_llm=after_llm)
        return Agent(
            pattern=self.pattern,
            tools=self.tools,
            model=wrapped,
            role=self.role,
            policy=self.policy,
            pattern_opts=self.pattern_opts,
            belief=self.belief,
            llm_text=text,
        )

    def run(
        self,
        question: str,
        /,
        *,
        scratchpad_prefix: str = "",
        initial_draft: str = "",
        validate: Optional[Callable[[str], Any]] = None,
        revise: Optional[Callable[[str, Any], str]] = None,
    ) -> AgentRunResult:
        strategy = get_strategy(self.pattern)
        ctx = AgentContext(
            question=question,
            registry=self.tools,
            llm_json=self.model,
            llm_text=self.llm_text,
            policy=self.policy,
            pattern_opts=self.pattern_opts or PATTERN_DEFAULTS[self.pattern],  # type: ignore[arg-type]
            belief=self.belief,
            scratchpad_prefix=scratchpad_prefix,
            initial_draft=initial_draft,
            validate=validate,
            revise=revise,
        )
        return strategy.run(ctx)
