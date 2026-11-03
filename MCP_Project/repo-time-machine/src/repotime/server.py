"""MCP tools for inspecting the configured Git repository."""

from fastmcp import FastMCP

from repotime.analysis.repository import (
    RepositoryStatus,
    get_repository_status as read_repository_status,
)
from repotime.config import get_repository_path
from repotime.resources.repository import register_repository_resources
from repotime.tools.git_tools import register_git_mcp_tools
from repotime.tools.ast_tools import register_ast_mcp_tools

mcp = FastMCP(
    "RepoTime Machine",
    instructions="Read basic information about the configured Git repository.",
    version="1.0",
)


@mcp.tool
def get_repository_name() -> str:
    """Return the name of the configured local Git repository."""
    return read_repository_status(get_repository_path()).name


@mcp.tool
def get_repository_status() -> RepositoryStatus:
    """Return the repository name, current branch, and clean working-tree state."""
    return read_repository_status(get_repository_path())

register_git_mcp_tools(mcp)
register_ast_mcp_tools(mcp)
register_repository_resources(mcp)

def main() -> None:
    """Serve MCP requests over standard input and output."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
