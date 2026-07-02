"""Native graph builder package."""

__all__ = ["Graph"]


def __getattr__(name: str):
    if name == "Graph":
        from chorusgraph.graph.builder import Graph

        return Graph
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
