"""MCP tools for inspecting the configured Git repository."""

from fastmcp import FastMCP

from repotime.analysis.repository import *
from repotime.analysis.git_diff_engine import *
from repotime.analysis.git_engine import *

from repotime.config import get_repository_path



def compare_revisions_tool(old_sha:str, new_sha:str) -> RevisionDiff:
    """Compare two commits and return one change record per affected file.

    Includes file status, line counts, and bounded patch text when available.

    Args:
        old_sha: Starting commit SHA or revision, such as HEAD~1.
        new_sha: Ending commit SHA or revision, such as HEAD.
    """
    return compare_revisions(get_repository_path(), old_sha, new_sha)



def get_commit_summary_tool(commit_sha: str) -> CommitSummary:
    """Return one commit's full SHA, subject line, and commit date.

    Args:
        commit_sha: Commit SHA or revision to inspect, such as HEAD.
    """
    return get_commit_summary(get_repository_path(), commit_sha)


def get_commit_list_tool(limit:int =50, offset = 0) -> CommitList:
    """List commits in Git log order with a has_more pagination flag.

    Args:
        limit: Maximum commits to return, from 1 to 100.
        offset: Number of commits to skip, from 0 to 10000.
    """
    return get_commit_list(get_repository_path(), limit=limit, offset=offset)


def get_commit_details_tool(commit_sha: str) -> CommitDetails:
    """Return a commit's author, message, parents, and changed file paths.

    Args:
        commit_sha: Commit SHA or revision to inspect, such as HEAD.
    """
    return get_commit_details(get_repository_path(), commit_sha)


def get_file_history_tool(file_path: str, limit: int = 50, offset: int = 0) -> FileHistory:
    """List commits that changed a file, with a has_more pagination flag.

    History follows the given path; it does not trace the file across renames.

    Args:
        file_path: Path relative to the configured repository root.
        limit: Maximum commits to return, from 1 to 100.
        offset: Number of matching commits to skip, from 0 to 10000.
    """
    return get_file_history(get_repository_path(), file_path=file_path, limit=limit, offset=offset)


def get_file_content_tool(file_path: str, commit_sha: str) -> FileContent:
    """Return a file's UTF-8 text at a commit, with the resolved commit SHA.

    Files larger than 1 MB and binary files are rejected.

    Args:
        file_path: Path relative to the configured repository root.
        commit_sha: Commit SHA or revision to read, such as HEAD.
    """
    return get_file_content(get_repository_path(), file_path=file_path, commit_sha=commit_sha)

def register_mcp_tools(mcp: FastMCP) -> None:
    """Register all MCP tools for inspecting the configured Git repository."""
    mcp.tool(compare_revisions_tool)
    mcp.tool(get_commit_summary_tool)
    mcp.tool(get_commit_list_tool)
    mcp.tool(get_commit_details_tool)
    mcp.tool(get_file_history_tool)
    mcp.tool(get_file_content_tool)