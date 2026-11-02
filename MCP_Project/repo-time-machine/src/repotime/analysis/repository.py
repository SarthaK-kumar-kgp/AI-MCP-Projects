"""Read basic facts about a local Git repository."""

from pathlib import Path

from git import InvalidGitRepositoryError, NoSuchPathError, Repo
from pydantic import BaseModel


class RepositoryStatus(BaseModel):
    name: str
    branch: str | None
    is_clean: bool


def get_repository_status(repo_path: Path) -> RepositoryStatus:
    """Return the name, current branch, and working-tree state."""
    try:
        repo = Repo(repo_path)
    except (InvalidGitRepositoryError, NoSuchPathError) as exc:
        raise ValueError(f"Not a Git repository: {repo_path}") from exc

    if repo.bare or repo.working_tree_dir is None:
        raise ValueError(f"A working-tree Git repository is required: {repo_path}")

    branch = None if repo.head.is_detached else repo.active_branch.name
    is_clean = not repo.is_dirty(untracked_files=False) and not repo.untracked_files
    return RepositoryStatus(
        name=Path(repo.working_tree_dir).name,
        branch=branch,
        is_clean=is_clean,
    )
