"""Compare two committed Git snapshots and report file-level changes."""

from pathlib import Path

from git import InvalidGitRepositoryError, NoSuchPathError, Repo
from git.exc import BadName, BadObject, GitCommandError
from pydantic import AwareDatetime, BaseModel


MAX_CHANGED_FILES = 100
MAX_PATCH_BYTES = 100_000


class FileDiff(BaseModel):
    """One file changed between two revisions."""

    file_path: str
    old_path: str | None
    new_path: str | None
    change_type: str
    additions: int | None
    deletions: int | None
    patch: str | None
    patch_truncated: bool = False


class RevisionDiff(BaseModel):
    """Bounded comparison of two committed snapshots."""

    old_sha: str
    new_sha: str
    old_date: AwareDatetime
    new_date: AwareDatetime
    files: list[FileDiff]


def compare_revisions(repo_path: Path, old_sha: str, new_sha: str) -> RevisionDiff:
    """Compare any two commits in the configured order, old to new."""
    for revision in (old_sha, new_sha):
        if (
            not isinstance(revision, str)
            or not revision.strip()
            or revision.startswith("-")
            or any(ord(char) < 32 for char in revision)
        ):
            raise ValueError("Revisions must be non-empty commit references")

    try:
        repo = Repo(repo_path)
    except (InvalidGitRepositoryError, NoSuchPathError) as exc:
        raise ValueError(f"Not a Git repository: {repo_path}") from exc

    try:
        old_commit = repo.commit(old_sha)
        new_commit = repo.commit(new_sha)
    except (BadName, BadObject, GitCommandError, ValueError) as exc:
        raise ValueError(f"Commit not found: {old_sha} or {new_sha}") from exc

    try:
        statuses = old_commit.diff(new_commit, find_renames=True)
        if len(statuses) > MAX_CHANGED_FILES:
            raise ValueError(f"Diff exceeds the {MAX_CHANGED_FILES}-file limit")
        patches = old_commit.diff(new_commit, create_patch=True, find_renames=True)
    except GitCommandError as exc:
        raise ValueError("Could not compare the requested commits") from exc

    # GitPython omits the missing side of an add/delete only in patch mode.
    patch_by_path = {
        (item.a_path or item.b_path, item.b_path or item.a_path): item.diff
        for item in patches
    }
    files = []
    used_patch_bytes = 0
    for item in statuses:
        key = (item.a_path or item.b_path, item.b_path or item.a_path)
        raw_patch = patch_by_path.get(key)
        if raw_patch is None:
            raise ValueError(f"Could not match patch for changed file: {key}")

        binary = b"Binary files " in raw_patch or b"GIT binary patch" in raw_patch
        if not binary:
            try:
                raw_patch.decode("utf-8")
            except UnicodeDecodeError:
                binary = True

        if binary:
            additions = deletions = None
            patch = None
            patch_truncated = False
        else:
            lines = raw_patch.splitlines()
            additions = sum(line.startswith(b"+") for line in lines)
            deletions = sum(line.startswith(b"-") for line in lines)
            remaining = MAX_PATCH_BYTES - used_patch_bytes
            selected = raw_patch[:remaining]
            used_patch_bytes += len(selected)
            patch = selected.decode("utf-8", errors="ignore")
            patch_truncated = len(selected) < len(raw_patch)

        old_path = None if item.change_type == "A" else item.a_path
        new_path = None if item.change_type == "D" else item.b_path
        files.append(
            FileDiff(
                file_path=new_path or old_path,
                old_path=old_path,
                new_path=new_path,
                change_type=item.change_type,
                additions=additions,
                deletions=deletions,
                patch=patch,
                patch_truncated=patch_truncated,
            )
        )

    return RevisionDiff(
        old_sha=old_commit.hexsha,
        new_sha=new_commit.hexsha,
        old_date=old_commit.committed_datetime,
        new_date=new_commit.committed_datetime,
        files=files,
    )
