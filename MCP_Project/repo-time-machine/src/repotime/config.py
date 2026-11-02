"""Configuration for the repository inspected by RepoTime Machine."""

import os
from pathlib import Path

from dotenv import load_dotenv


def get_repository_path() -> Path:
    """Return the configured, existing repository directory."""
    load_dotenv()
    raw_path = os.getenv("REPOSITORY_PATH")
    if raw_path is None or not raw_path.strip():
        raise ValueError("REPOSITORY_PATH environment variable is not set.")

    repository_path = Path(raw_path).expanduser().resolve()
    if not repository_path.is_dir():
        raise ValueError(f"Repository path is not an existing directory: {repository_path}")

    return repository_path
