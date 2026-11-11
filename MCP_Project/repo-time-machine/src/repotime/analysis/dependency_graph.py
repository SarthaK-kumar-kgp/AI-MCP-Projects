"""Build a read-only Python call graph and query function relationships."""

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict

import networkx as nx
from cldk import CLDK
from cldk.analysis import AnalysisLevel
from cldk.analysis.commons.backend_config import PyCodeAnalyzerConfig
from git import InvalidGitRepositoryError, NoSuchPathError, Repo
from pydantic import BaseModel


class CallRelations(BaseModel):
    """Functions reached through confirmed call edges in one direction."""

    function: str
    direct: list[str]
    indirect: list[str]
    external: list[str]
    truncated: bool


class FunctionSearchResult(BaseModel):
    """Matching repository function identifiers from the call graph."""

    query: str
    matches: list[str]
    truncated: bool


def build_dependency_graph(
    repo_path: Path, source_root: str | Path | None = None
) -> nx.DiGraph:
    """Analyze one local repository without writing files into it.

    ``source_root`` is the folder Python imports start from, relative to the
    repository unless an absolute path inside it is supplied. By default,
    use ``src`` when present and the repository root otherwise.
    """
    try:
        repo = Repo(repo_path)
    except (InvalidGitRepositoryError, NoSuchPathError) as exc:
        raise ValueError(f"Not a Git repository: {repo_path}") from exc
    if repo.bare or repo.working_tree_dir is None:
        raise ValueError("A working-tree Git repository is required")

    repo_root = Path(repo.working_tree_dir).resolve()
    root = Path(source_root) if source_root is not None else (
        Path("src") if (repo_root / "src").is_dir() else Path(".")
    )
    source_path = (root if root.is_absolute() else repo_root / root).resolve()
    if not source_path.is_relative_to(repo_root) or not source_path.is_dir():
        raise ValueError("source_root must be an existing directory inside the repository")

    # codeanalyzer needs a base Python to create its analysis environment.
    os.environ.setdefault("SYSTEM_PYTHON", sys._base_executable)

    with TemporaryDirectory(prefix="repotime-cldk-") as cache_dir:
        analysis = CLDK.python(
            project_path=source_path,
            analysis_level=AnalysisLevel.call_graph,
            backend=PyCodeAnalyzerConfig(cache_dir=cache_dir),
        )
        graph = analysis.get_call_graph()

    graph.graph["source_root"] = str(source_path.relative_to(repo_root))
    return graph

def graph_to_json(graph:nx.DiGraph) -> Dict:
    graph_in_json = nx.node_link_data(graph)
    return graph_in_json


def search_graph_functions(
    graph: nx.DiGraph, query: str, limit: int = 20
) -> FunctionSearchResult:
    """Find repository functions whose graph identifier contains ``query``."""
    query = query.strip()
    if not query:
        raise ValueError("query must not be empty")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    matches = sorted(
        node for node in graph
        if isinstance(node, str)
        and "/@external/" not in node
        and query.casefold() in node.casefold()
    )
    return FunctionSearchResult(
        query=query, matches=matches[:limit], truncated=len(matches) > limit
    )




def _relations(
    graph: nx.DiGraph, function: str, depth: int, limit: int, *, callers: bool
) -> CallRelations:
    if function not in graph or "/@external/" in function:
        raise ValueError(f"Function is not in the repository call graph: {function}")
    if not 1 <= depth <= 5:
        raise ValueError("depth must be between 1 and 5")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    direct: list[str] = []
    indirect: list[str] = []
    external: list[str] = []
    visited = {function}
    frontier = [function]
    for distance in range(1, depth + 1):
        next_frontier: list[str] = []
        for current in frontier:
            neighbors = graph.predecessors(current) if callers else graph.successors(current)
            for neighbor in sorted(neighbors):
                if neighbor in visited:
                    continue
                if len(visited) - 1 >= limit:
                    return CallRelations(
                        function=function,
                        direct=direct,
                        indirect=indirect,
                        external=external,
                        truncated=True,
                    )
                visited.add(neighbor)
                if "/@external/" in neighbor:
                    external.append(neighbor)
                elif distance == 1:
                    direct.append(neighbor)
                    next_frontier.append(neighbor)
                else:
                    indirect.append(neighbor)
                    next_frontier.append(neighbor)
        frontier = next_frontier

    return CallRelations(
        function=function,
        direct=direct,
        indirect=indirect,
        external=external,
        truncated=False,
    )


def get_function_dependencies(
    graph: nx.DiGraph, function: str, depth: int = 2, limit: int = 100
) -> CallRelations:
    """List functions called directly or indirectly by ``function``."""
    return _relations(graph, function, depth, limit, callers=False)


def analyze_change_impact(
    graph: nx.DiGraph, function: str, depth: int = 2, limit: int = 100
) -> CallRelations:
    """List potential direct and indirect callers of a changed function."""
    return _relations(graph, function, depth, limit, callers=True)
