"""Git history result models and operations."""

from pathlib import Path

from git import InvalidGitRepositoryError, NoSuchPathError, Repo
from git.exc import BadName, BadObject, GitCommandError
from pydantic import AwareDatetime, BaseModel


MAX_PAGE_SIZE = 100
MAX_OFFSET = 10_000
MAX_FILE_BYTES = 1_000_000

class CommitSummary(BaseModel):
    """A compact commit entry for history lists."""
    sha: str
    subject: str
    date: AwareDatetime

class CommitList(BaseModel):
    """A bounded page of commits."""
    commits: list[CommitSummary]
    has_more: bool = False

class CommitDetails(BaseModel):
    """Metadata and changed paths for one commit."""
    sha: str
    author_name: str
    author_email: str | None
    date: AwareDatetime
    message: str
    parent_shas: list[str]
    changed_files: list[str]

class FileHistory(BaseModel):
    """A bounded page of commits that changed a file."""
    file_path: str
    commits: list[CommitSummary]
    has_more: bool = False

class FileContent(BaseModel):
    """Text content of a file at a specific commit."""
    file_path: str
    commit_sha: str
    content: str

def _open_repo(repo_path: Path) -> Repo:
    try:
        return Repo(repo_path)
    except (InvalidGitRepositoryError, NoSuchPathError) as exc:
        raise ValueError(f"Not a Git repository: {repo_path}") from exc


def _resolve_commit(repo: Repo, commit_sha: str):
    if not isinstance(commit_sha, str) or not commit_sha.strip():
        raise ValueError("commit_sha must be a non-empty revision")
    if commit_sha.startswith("-") or any(ord(char) < 32 for char in commit_sha):
        raise ValueError("Invalid commit revision")
    try:
        return repo.commit(commit_sha)
    except (BadName, BadObject, GitCommandError, ValueError) as exc:
        raise ValueError(f"Commit not found: {commit_sha}") from exc


def _validate_page(limit: int, offset: int) -> None:
    if not 1 <= limit <= MAX_PAGE_SIZE:
        raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}")
    if not 0 <= offset <= MAX_OFFSET:
        raise ValueError(f"offset must be between 0 and {MAX_OFFSET}")


def _validate_file_path(file_path: str) -> None:
    if (
        not isinstance(file_path, str)
        or len(file_path) > 1024
        or "\\" in file_path
        or any(ord(char) < 32 for char in file_path)
        or any(part in {"", ".", ".."} for part in file_path.split("/"))
    ):
        raise ValueError("file_path must be a repository-relative path without traversal")


def _summarize(commit) -> CommitSummary:
    return CommitSummary(
        sha=commit.hexsha,
        subject=commit.summary,
        date=commit.committed_datetime,
    )


def get_commit_summary(repo_path: Path, commit_sha: str) -> CommitSummary:
    repo = _open_repo(repo_path)
    return _summarize(_resolve_commit(repo, commit_sha))


def get_commit_list(repo_path: Path, limit: int = 50, offset: int = 0) -> CommitList:
    _validate_page(limit, offset)
    repo = _open_repo(repo_path)
    if not repo.head.is_valid():
        return CommitList(commits=[])
    commits = list(repo.iter_commits(max_count=limit + 1, skip=offset))
    return CommitList(
        commits=[_summarize(commit) for commit in commits[:limit]],
        has_more=len(commits) > limit,
    )


def get_commit_details(repo_path: Path, commit_sha: str) -> CommitDetails:
    repo = _open_repo(repo_path)
    commit = _resolve_commit(repo, commit_sha)
    return CommitDetails(
        sha=commit.hexsha,
        author_name=commit.author.name,
        author_email=commit.author.email,
        date=commit.committed_datetime,
        message=commit.message,
        parent_shas=[parent.hexsha for parent in commit.parents],
        changed_files=list(commit.stats.files),
    )


def get_file_history(
    repo_path: Path, file_path: str, limit: int = 50, offset: int = 0
) -> FileHistory:
    _validate_file_path(file_path)
    _validate_page(limit, offset)
    repo = _open_repo(repo_path)
    if not repo.head.is_valid():
        return FileHistory(file_path=file_path, commits=[])
    commits = list(
        repo.iter_commits(
            paths=f":(literal){file_path}", max_count=limit + 1, skip=offset
        )
    )
    return FileHistory(
        file_path=file_path,
        commits=[_summarize(commit) for commit in commits[:limit]],
        has_more=len(commits) > limit,
    )


def get_file_content(repo_path: Path, file_path: str, commit_sha: str) -> FileContent:
    _validate_file_path(file_path)
    repo = _open_repo(repo_path)
    commit = _resolve_commit(repo, commit_sha)
    try:
        blob = commit.tree / file_path
    except KeyError as exc:
        raise ValueError(f"File '{file_path}' not found in commit '{commit_sha}'") from exc
    if blob.type != "blob":
        raise ValueError(f"Path is not a file: {file_path}")
    if blob.size > MAX_FILE_BYTES:
        raise ValueError(f"File exceeds the {MAX_FILE_BYTES}-byte limit: {file_path}")
    raw_content = blob.data_stream.read(MAX_FILE_BYTES + 1)
    if len(raw_content) > MAX_FILE_BYTES:
        raise ValueError(f"File exceeds the {MAX_FILE_BYTES}-byte limit: {file_path}")
    if b"\x00" in raw_content:
        raise ValueError(f"File is not UTF-8 text: {file_path}")
    try:
        content = raw_content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"File is not UTF-8 text: {file_path}") from exc
    return FileContent(file_path=file_path, commit_sha=commit.hexsha, content=content)
