"""Read-only repository resources backed by the Git analysis functions."""

from fastmcp import FastMCP

from repotime.analysis.git_engine import get_commit_details, get_file_content
from repotime.analysis.repository import get_repository_status
from repotime.config import get_repository_path


def register_repository_resources(mcp: FastMCP) -> None:
    """Register metadata and historical Git evidence on the existing server."""

    @mcp.resource("repo://metadata", mime_type="application/json")
    def repository_metadata() -> dict:
        """Current name, branch, and working-tree state of the configured repository."""
        return get_repository_status(get_repository_path()).model_dump(mode="json")

    @mcp.resource("repo://commit/{sha}", mime_type="application/json")
    def commit_at_revision(sha: str) -> dict:
        """Commit metadata, parents, and changed file paths for a revision."""
        return get_commit_details(get_repository_path(), sha).model_dump(mode="json")

    @mcp.resource("repo://file/{sha}/{path*}", mime_type="text/plain")
    def file_at_revision(sha: str, path: str) -> str:
        """UTF-8 file text at a revision; path is relative to the repository root."""
        return get_file_content(get_repository_path(), path, sha).content
