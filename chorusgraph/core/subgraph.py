"""Local and remote subgraph composition — Improve-1 T4/T5."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, TYPE_CHECKING

from chorusgraph.core.channels import NodeUpdate
from chorusgraph.core.envelope import compact_json
from chorusgraph.core.node import NodeContext, NodeFn, native_node

if TYPE_CHECKING:
    from chorusgraph.core.scheduler import CompiledGraph


SubgraphLocation = str  # "local" | "chorus" | "prismapi"


@dataclass(frozen=True)
class SubgraphSpec:
    name: str
    child: "CompiledGraph"
    input_map: Mapping[str, str]
    output_map: Mapping[str, str]
    location: SubgraphLocation = "local"


def namespaced_thread_id(parent_thread: str, node_name: str) -> str:
    safe_parent = parent_thread.replace(":", "__")
    return f"{safe_parent}__{node_name}"


def _parent_thread_id(config: Optional[Dict[str, Any]]) -> str:
    if not config:
        return "default"
    return str(config.get("configurable", {}).get("thread_id") or "default")


def _boundary_artifact(parent_view: Dict[str, Any]) -> Dict[str, Any]:
    seq = parent_view.get("prism_sequence") or []
    primary = seq[-1] if seq else {}
    artifact: Dict[str, Any] = {"raw_output": parent_view.get("raw_output") or compact_json(parent_view)}
    if primary:
        artifact["envelope_id"] = primary.get("envelope_id")
        artifact["vector"] = list(primary.get("vector") or [])
        artifact["category_slug"] = primary.get("category_slug")
    return artifact


def _maybe_reproject(artifact: Dict[str, Any], *, translator: Any = None) -> Dict[str, Any]:
    if translator is None:
        return artifact
    try:
        from prismlang import PrismState

        state = PrismState(
            prism_sequence=[],
            raw_output=str(artifact.get("raw_output") or ""),
            tenant_id=str(artifact.get("tenant_id") or "default"),
        )
        translated = translator.translate(state)
        if translated:
            out = dict(artifact)
            out["raw_output"] = translated
            return out
    except Exception:
        return artifact
    return artifact


def _map_child_input(
    parent_view: Dict[str, Any],
    input_map: Mapping[str, str],
    *,
    boundary: Dict[str, Any],
) -> Dict[str, Any]:
    child_input: Dict[str, Any] = dict(boundary)
    for parent_key, child_key in input_map.items():
        if parent_key in parent_view:
            child_input[child_key] = parent_view[parent_key]
    return child_input


def _child_values_to_update(
    ctx: NodeContext,
    child_values: Dict[str, Any],
    output_map: Mapping[str, str],
    *,
    subgraph_name: str,
) -> NodeUpdate:
    artifact: Dict[str, Any] = {"subgraph": subgraph_name}
    for child_key, parent_key in output_map.items():
        if child_key in child_values:
            artifact[parent_key] = child_values[child_key]
    for parent_key in output_map.values():
        if parent_key in child_values and parent_key not in artifact:
            artifact[parent_key] = child_values[parent_key]
    return ctx.publish(
        artifact=artifact,
        category_slug=str(child_values.get("category_slug") or "general"),
        rule_chain=[f"subgraph:{subgraph_name}"],
    )


def build_subgraph_node(spec: SubgraphSpec, *, boundary_translator: Any = None) -> NodeFn:
    """Create a native node that invokes ``spec.child`` with explicit channel maps."""

    @native_node
    def subgraph_node(ctx: NodeContext) -> NodeUpdate:
        parent_view = ctx.read()
        boundary = _maybe_reproject(_boundary_artifact(parent_view), translator=boundary_translator)
        child_input = _map_child_input(parent_view, spec.input_map, boundary=boundary)

        parent_thread = _parent_thread_id(ctx.run_config)
        child_thread = namespaced_thread_id(parent_thread, spec.name)
        child_config = dict(ctx.run_config or {})
        child_config.setdefault("configurable", {})
        child_config["configurable"] = dict(child_config["configurable"])
        child_config["configurable"]["thread_id"] = child_thread

        parent_run_id = getattr(ctx, "parent_run_id", None) or (
            ctx.run_config.get("_parent_run_id") if ctx.run_config else None
        )

        if spec.location != "local":
            from chorusgraph.core.subgraph_transport import invoke_remote_subgraph

            child_values = invoke_remote_subgraph(
                spec,
                child_input,
                config=child_config,
                parent_run_id=parent_run_id,
            )
        else:
            child_in = dict(child_input)
            if ctx.resume_value is not None:
                child_in["__resume__"] = ctx.resume_value
            try:
                child_values = spec.child.invoke(
                    child_in,
                    config=child_config,
                    _parent_run_id=parent_run_id,
                    _subgraph_node=spec.name,
                )
            except Exception as exc:
                from chorusgraph.core.scheduler import GraphInterrupt

                if not isinstance(exc, GraphInterrupt):
                    raise
                path = namespaced_thread_id(parent_thread, spec.name)
                raise GraphInterrupt(
                    exc.state,
                    next_nodes=exc.next_nodes,
                    super_step=exc.super_step,
                    payload={"subgraph_path": path, "inner": exc.payload},
                ) from exc

        if child_values.get("__interrupt__"):
            from chorusgraph.core.scheduler import GraphInterrupt

            path = namespaced_thread_id(parent_thread, spec.name)
            raise GraphInterrupt(
                child_values,
                next_nodes=set(child_values.get("__next__") or []),
                super_step=ctx.super_step,
                payload={"subgraph_path": path, "inner": child_values.get("__interrupt_payload__")},
            )

        return _child_values_to_update(ctx, child_values, spec.output_map, subgraph_name=spec.name)

    subgraph_node._subgraph_spec = spec  # type: ignore[attr-defined]
    return subgraph_node


__all__ = [
    "SubgraphLocation",
    "SubgraphSpec",
    "build_subgraph_node",
    "namespaced_thread_id",
]
