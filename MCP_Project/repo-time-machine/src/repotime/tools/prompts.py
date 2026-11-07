"""MCP prompts which aids the host for more efficeint usage of MCP tools."""

from fastmcp import FastMCP


def functional_dependency_prompt(function: str) -> str:
    """Guide an investigation of a function's dependencies and possible impact."""
    return (
        f"Investigate the project function {function!r}. "
        "Use get_functional_dependency_tool to find functions it calls, and "
        "get_change_impact_tool to find functions that call it. "
        "Explain direct and indirect relationships separately. "
        "Describe callers as possibly affected if the function changes, "
        "not as functions that are certain to break. "
        "Mention that static analysis may miss dynamic or unresolved calls."
    )

def git_commit_prompt(commit_sha: str) -> str:
    """Guide a summary of one commit's metadata."""
    return (
        f"Summarize Git commit {commit_sha!r}. "
        "Use get_commit_details_tool for its author, message, parents, and changed file paths. "
        "Use get_commit_summary_tool for its subject and date. "
        "Describe what this metadata shows without claiming which code lines changed."
    )


def change_comparison_prompt(old_sha:str, new_sha:str, file_path: str)-> str:
    """Guide an investigation of a file's changes between two commits."""
    return (
        f"Compare commits {old_sha!r} and {new_sha!r} for file {file_path!r}. "
        "Call compare_revisions_tool with the two SHAs; its result covers all changed files. "
        f"Find the entry for {file_path!r}, checking old_path and new_path if it was renamed, "
        "then explain its change type and patch. "
        f"Use get_file_history_tool for {file_path!r} to show commits that changed this path; "
        "its history does not follow renames. "
        "If the patch needs more context, use get_file_content_tool at each SHA where the file exists. "
        "Base the explanation on the returned evidence."
    )

def function_evolution_prompt(file_path: str, target_fxn: str) -> str:
    """Guide an investigation of a function's evolution across commits."""
    return (
        f"Trace the evolution of function {target_fxn!r} in file {file_path!r}. "
        "Use trace_function_evolution_tool to find commits that changed this function, "
        "then explain the changes in each commit. "
        "This trace follows one file path and function name; explain that renames or moves may make it incomplete. "
        "If the patch needs more context, use get_file_content_tool at each SHA where the file exists. "
        "Base the explanation on the returned evidence."
    )

def function_info_comparison_prompt(old_sha:str, new_sha:str, file_path: str, target_fxn: str) -> str:
    """Guide an investigation of a function's changes between two commits."""
    return (
        f"Compare function {target_fxn!r} in file {file_path!r} between commits {old_sha!r} and {new_sha!r}. "
        "Use get_function_comparison_tool to find its change type and patch, "
        "then explain the changes. "
        "If the patch needs more context, use get_file_content_tool at each SHA where the file exists. "
        "Base the explanation on the returned evidence."
    )

def register_prompt_mcp_tools(mcp: FastMCP) -> None:
    """Register the prompts on the MCP server."""
    mcp.prompt(functional_dependency_prompt)
    mcp.prompt(git_commit_prompt)
    mcp.prompt(change_comparison_prompt)
    mcp.prompt(function_evolution_prompt)
    mcp.prompt(function_info_comparison_prompt)
