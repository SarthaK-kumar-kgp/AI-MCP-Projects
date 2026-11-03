"""MCP tools for inspecting the evolution of functions in the configured Git repository."""

from fastmcp import FastMCP

from repotime.analysis.repository import *
from repotime.analysis.ast_engine import *

from repotime.config import get_repository_path



def get_target_function_tool(commit_sha:str, file_path: str, target_fxn: str) -> FindFunction | None:
    """Find one Python function at a revision and return its source and location.

    Return null when the function is absent from an existing file.

    Args:
        commit_sha: Commit SHA or revision to inspect.
        file_path: Path relative to the configured repository root.
        target_fxn: Qualified name, or a short name if it is unambiguous.
    """
    return get_target_function(get_repository_path(), commit_sha, file_path, target_fxn)



def get_function_comparison_tool(old_sha:str, new_sha:str, file_path: str, target_fxn: str) -> FunctionComparison:
    """Compare a function at two revisions and return change types and a source diff.

    Args:
        old_sha: Starting commit SHA or revision, such as HEAD~1.
        new_sha: Ending commit SHA or revision, such as HEAD.
        file_path: Path relative to the configured repository root.
        target_fxn: Qualified name, or a short name if it is unambiguous.
    """
    return get_function_comparison(get_repository_path(), old_sha, new_sha, file_path, target_fxn)


def trace_function_evolution_tool(    file_path: str,
    target_fxn: str,
    limit: int = 50,
    offset: int = 0,) -> FunctionEvolution:
    """Trace commits that changed a function, oldest to newest within each page.

    Pages select the newest file commits first. Unchanged functions are omitted;
    has_more indicates that older file commits remain.

    Args:
        file_path: Path relative to the configured repository root.
        target_fxn: Qualified name, or a short name if it is unambiguous.
        limit: Maximum file commits to inspect, from 1 to 100.
        offset: Number of newer file commits to skip, from 0 to 10000.
    """
    return trace_function_evolution(get_repository_path(), file_path=file_path, target_fxn=target_fxn, limit=limit, offset=offset)


def register_ast_mcp_tools(mcp: FastMCP) -> None:
    """Register the function lookup, comparison, and evolution tools."""
    mcp.tool(get_target_function_tool)
    mcp.tool(get_function_comparison_tool)
    mcp.tool(trace_function_evolution_tool)
