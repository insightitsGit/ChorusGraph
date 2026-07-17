"""Catalog of use cases for ReAct, Plan-and-Solve, Reflection, and multi-agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class UseCase:
    """One pattern + a concrete product scenario."""

    pattern: str  # react | plan_solve | reflection | multi_agent | cache | warm_chunks | cortex
    title: str
    domain: str
    question: str
    why: str
    topology: str
    when_to_use: str
    stop_condition: str


USE_CASES: List[UseCase] = [
    UseCase(
        pattern="react",
        title="Compare live FX rates (unknown tool order)",
        domain="Finance / rates",
        question="Compare USD/EUR and USD/GBP - which is stronger against USD?",
        why=(
            "The agent must decide which tools to call and in what order. "
            "ReAct loops Thought -> Action -> Observation until it can finish."
        ),
        topology="reason <-> tool -> finish -> writer / validator",
        when_to_use="1-N tool calls, order unknown; exploration and comparisons",
        stop_condition="LLM sets finish=true, or PlanPolicy max_steps / token budget",
    ),
    UseCase(
        pattern="plan_solve",
        title="Fetch rates then compute a cross-rate (fixed steps)",
        domain="Finance / pricing",
        question="Fetch USD/EUR and USD/GBP, compute EUR/GBP cross-rate, summarize.",
        why=(
            "The work decomposes into an explicit checklist. Plan-and-Solve emits "
            "a static plan once, then executes steps sequentially - cacheable and auditable."
        ),
        topology="planner -> step1 -> step2 -> ... -> writer",
        when_to_use="Decomposable tasks with a known tool catalog and fixed pipeline",
        stop_condition="All plan steps done, or on_step_failure / max_plan_steps",
    ),
    UseCase(
        pattern="reflection",
        title="Draft FX summary must pass a rate validator",
        domain="Finance / compliance-sensitive copy",
        question="Summarize USD/EUR and USD/GBP; reject drafts with wrong figures.",
        why=(
            "Quality-sensitive answers need a generator -> critic loop. Reflection "
            "revises until a validator (or grounding guard) approves the draft."
        ),
        topology="draft -> validator <-> revise -> approved draft",
        when_to_use="Drafts with rates, citations, or compliance claims that must be checked",
        stop_condition="Validator approves, or max_revisions / max_reflection_passes",
    ),
    UseCase(
        pattern="multi_agent",
        title="Researcher -> Writer -> Validator role pipeline",
        domain="Multi-agent / role orchestration",
        question="Explain ChorusGraph engine - plan research, draft answer, validate.",
        why=(
            "Specialized role nodes collaborate on a fixed graph. Each role publishes "
            "envelopes on the Resonance bus; the Route Ledger records every hop."
        ),
        topology="START -> researcher -> writer -> validator -> END",
        when_to_use="Known multi-hop pipelines with distinct roles (not a dynamic Agent loop)",
        stop_condition="Graph reaches END; validator publishes approval artifact",
    ),
    UseCase(
        pattern="cache",
        title="Built-in semantic cache (miss then hit)",
        domain="L1 PrismCache / cache_gate",
        question="What is the USD to EUR exchange rate today?",
        why=(
            "ChorusStack ships PrismCache by default. cache_gate does coarse 64-d recall "
            "then full verify. On a hit, graphs skip researcher/ReAct and go straight to writer."
        ),
        topology="vector_ingress -> cache_gate -[hit]-> writer | -[miss]-> agent/tools",
        when_to_use="Repeat or paraphrase queries; cut LLM tokens and latency on known intents",
        stop_condition="Hit returns cached value; miss continues the graph (then seed after tools)",
    ),
    UseCase(
        pattern="warm_chunks",
        title="Warm chunk vectors (index once, query-only retrieve)",
        domain="L2 retrieval / ADR-005",
        question="How does PrismCache reduce LLM costs?",
        why=(
            "Stable knowledge bases should not re-encode the corpus every turn. "
            "Index by partition/version, warm_retrieval at worker boot, retrieve with "
            "query-only embeds (rerank_policy=vectors_only on PrismRAG)."
        ),
        topology="index(partition,version) -> warm_retrieval -> retrieve(query-only)",
        when_to_use="Production RAG with a mostly stable KB; multi-replica workers needing ready probes",
        stop_condition="retrieval_ready(partition); same version index is a no-op",
    ),
    UseCase(
        pattern="cortex",
        title="PrismCortex L3 - recall at ingress, digest off the hot path",
        domain="L3 memory / PrismCortex",
        question="What is my risk tolerance?",
        why=(
            "User/session facts belong in Cortex, not the L1 whole-answer cache. "
            "Recall structured evidence at ingress (confidence/freshness); schedule_digest "
            "asynchronously after the response so memory write-back never adds latency."
        ),
        topology="ingress recall_structured -> hops -> response -> async schedule_digest",
        when_to_use="Personalized agents, cross-session preference/facts, compliance provenance",
        stop_condition="confidence/freshness gate; empty recall continues without fake fallbacks",
    ),
]


def by_pattern(pattern: str) -> UseCase:
    for uc in USE_CASES:
        if uc.pattern == pattern:
            return uc
    raise KeyError(f"Unknown pattern: {pattern}")
