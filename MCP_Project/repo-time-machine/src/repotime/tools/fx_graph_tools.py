"""MCP wrappers for Python function dependencies and potential change impact."""

from fastmcp import FastMCP
from typing import Dict
from repotime.analysis.dependency_graph import (
    CallRelations,
    FunctionSearchResult,
    analyze_change_impact,
    build_dependency_graph,
    get_function_dependencies,
    graph_to_json,
    search_graph_functions,
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

def get_graph_to_json_tool() -> Dict:
    """Return the configured repository's function call graph as JSON data.

    Use this when the complete set of functions and caller-to-callee edges is
    needed. For finding an exact function identifier, use
    search_graph_functions_tool instead; this result may be large.
    """
    graph  = build_dependency_graph(get_repository_path())
    return graph_to_json(graph)


def search_graph_functions_tool(query: str, limit: int = 20) -> FunctionSearchResult:
    """Find exact function identifiers for the dependency and change-impact tools.

    Search by a function name or part of a dotted module path. For example,
    ``calculate_total`` can match ``shop.pricing.calculate_total``. Multiple
    matches may be returned; use the relevant full identifier in the next tool.

    Args:
        query: Function name or module-path fragment to find.
        limit: Maximum matches to return, from 1 to 100.
    """
    graph = build_dependency_graph(get_repository_path())
    return search_graph_functions(graph, query, limit)


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
    """Register function search, dependency, impact, and graph tools."""
    mcp.tool(search_graph_functions_tool)
    mcp.tool(get_functional_dependency_tool)
    mcp.tool(get_change_impact_tool)
    mcp.tool(get_graph_to_json_tool)
