"""MCP wrappers for Python function dependencies and potential change impact."""

from fastmcp import FastMCP

from repotime.analysis.dependency_graph import (
    CallRelations,
    analyze_change_impact,
    build_dependency_graph,
    get_function_dependencies,
)
from repotime.config import get_repository_path


def get_functional_dependency_tool(function: str, depth: int = 2, limit: int = 100) -> CallRelations:
    """List functions called directly or indirectly by a project function.

    Args:
        function: Function identifier from the call graph.
        depth: Maximum number of call steps to follow, from 1 to 5.
        limit: Maximum number of related functions to return, from 1 to 100.
    """
    graph = build_dependency_graph(get_repository_path())
    return get_function_dependencies(graph, function, depth, limit)

def get_change_impact_tool(function: str, depth: int = 2, limit: int = 100) -> CallRelations:
    """List functions that may be affected if a project function changes.

    Args:
        function: Changed function's identifier from the call graph.
        depth: Maximum number of caller steps to follow, from 1 to 5.
        limit: Maximum number of related functions to return, from 1 to 100.
    """
    graph = build_dependency_graph(get_repository_path())
    return analyze_change_impact(graph, function, depth, limit)


def register_graph_mcp_tools(mcp: FastMCP) -> None:
    """Register the dependency and change-impact tools on the MCP server."""
    mcp.tool(get_functional_dependency_tool)
    mcp.tool(get_change_impact_tool)
