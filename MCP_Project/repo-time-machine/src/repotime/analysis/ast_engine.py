"""Read Python function snapshots from historical Git files."""

import ast
import difflib
import io
import textwrap
import tokenize
from pathlib import Path

from pydantic import BaseModel

from repotime.analysis.git_engine import (
    get_commit_details,
    get_file_content,
    get_file_history,
)


class FindFunction(BaseModel):
    """The location and source of one function at one commit."""
    name: str
    qualified_name: str
    file_path: str
    commit_sha: str
    start_line: int
    end_line: int
    source: str

class FunctionComparison(BaseModel):
    """A function's categorized and exact source changes between two commits."""
    function_name: str
    commit_sha1: str
    commit_sha2: str
    function1: FindFunction | None
    function2: FindFunction | None
    changes: list[str] | None
    source_diff: str | None
    has_changes: bool
    file_name: str


class FunctionEvolutionEntry(BaseModel):
    """One commit where the selected function changed."""
    commit_sha: str
    previous_sha: str | None
    function: FindFunction | None
    changes: list[str]
    source_diff: str | None


class FunctionEvolution(BaseModel):
    """Chronological function changes within a page of file history."""
    file_path: str
    function_name: str
    entries: list[FunctionEvolutionEntry]
    has_more: bool

def get_target_function(
    repo_path: Path, commit_sha: str, file_path: str, target_fxn: str
) -> FindFunction | None:
    """Find a function by qualified name, or by an unambiguous bare name."""
    if not target_fxn or not target_fxn.strip():
        raise ValueError("target_fxn must be a non-empty function name")

    content = get_file_content(repo_path, file_path, commit_sha)
    try:
        tree = ast.parse(content.content, filename=file_path)
    except SyntaxError as exc:
        raise ValueError(
            f"Cannot parse {file_path} at {content.commit_sha}, line {exc.lineno}: {exc.msg}"
        ) from exc

    matches: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []

    class FunctionFinder(ast.NodeVisitor):
        def __init__(self) -> None:
            self.scope: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.scope.append(node.name)
            for child in node.body:
                self.visit(child)
            self.scope.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            qualified_name = ".".join([*self.scope, node.name])
            if target_fxn in {node.name, qualified_name}:
                matches.append((qualified_name, node))
            self.scope.append(node.name)
            for child in node.body:
                self.visit(child)
            self.scope.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

    FunctionFinder().visit(tree)
    if not matches:
        return None
    if len(matches) > 1:
        names = ", ".join(name for name, _ in matches)
        raise ValueError(f"Ambiguous function name '{target_fxn}'; use one of: {names}")

    qualified_name, node = matches[0]
    start_line = min(
        [node.lineno, *(decorator.lineno for decorator in node.decorator_list)]
    )
    lines = content.content.splitlines(keepends=True)
    end_line = node.end_lineno
    for line_number in range(end_line + 1, len(lines) + 1):
        line = lines[line_number - 1]
        stripped = line.lstrip()
        if not stripped:
            continue
        if stripped.startswith("#") and len(line) - len(stripped) > node.col_offset:
            end_line = line_number
            continue
        break
    source = "".join(lines[start_line - 1 : end_line])
    return FindFunction(
        name=node.name,
        qualified_name=qualified_name,
        file_path=file_path,
        commit_sha=content.commit_sha,
        start_line=start_line,
        end_line=end_line,
        source=source,
    )

def get_function_comparison(
    repo_path: Path, commit_sha1: str, commit_sha2: str, file_path: str, target_fxn: str
) -> FunctionComparison:
    """Describe every source-line change and the kinds of syntax that changed."""
    function1 = get_target_function(repo_path, commit_sha1, file_path, target_fxn)
    function2 = get_target_function(repo_path, commit_sha2, file_path, target_fxn)
    old_source = function1.source if function1 else ""
    new_source = function2.source if function2 else ""
    source_diff = "".join(
        difflib.unified_diff(
            old_source.splitlines(keepends=True),
            new_source.splitlines(keepends=True),
            fromfile=commit_sha1,
            tofile=commit_sha2,
        )
    ) or None
    changes: list[str] = []

    if function1 and function2 and source_diff:
        def describe(source: str) -> tuple[str, str | None, list[str], list[str], str]:
            node = ast.parse(textwrap.dedent(source)).body[0]
            signature = (
                f"{'async ' if isinstance(node, ast.AsyncFunctionDef) else ''}"
                f"def {node.name}({ast.unparse(node.args)})"
            )
            if node.returns:
                signature += f" -> {ast.unparse(node.returns)}"
            docstring = ast.get_docstring(node, clean=False)
            decorators = [ast.unparse(item) for item in node.decorator_list]
            comments = [
                token.string
                for token in tokenize.generate_tokens(io.StringIO(source).readline)
                if token.type == tokenize.COMMENT
            ]
            body = node.body[1:] if docstring is not None else node.body
            body_syntax = ast.dump(ast.Module(body=body, type_ignores=[]))
            return signature, docstring, decorators, comments, body_syntax

        old_signature, old_docstring, old_decorators, old_comments, old_body = describe(old_source)
        new_signature, new_docstring, new_decorators, new_comments, new_body = describe(new_source)
        if old_signature != new_signature:
            changes.append(f"Signature changed: {old_signature} → {new_signature}")
        if old_docstring != new_docstring:
            changes.append("Docstring changed")
        if old_decorators != new_decorators:
            changes.append("Decorators changed")
        if old_comments != new_comments:
            changes.append("Comments changed")
        if old_body != new_body:
            changes.append("Function body syntax changed")
        if not changes:
            changes.append("Formatting changed")
    elif function1 and not function2:
        changes.append(f"Function '{target_fxn}' was removed")
    elif function2 and not function1:
        changes.append(f"Function '{target_fxn}' was added")

    return FunctionComparison(
        function_name=target_fxn,
        commit_sha1=commit_sha1,
        commit_sha2=commit_sha2,
        function1=function1,
        function2=function2,
        changes=changes or None,
        source_diff=source_diff,
        has_changes=bool(source_diff),
        file_name=file_path,
    )


def trace_function_evolution(
    repo_path: Path,
    file_path: str,
    target_fxn: str,
    limit: int = 50,
    offset: int = 0,
) -> FunctionEvolution:
    """Trace changes to one function across a bounded page of file commits."""
    history = get_file_history(repo_path, file_path, limit=limit, offset=offset)
    entries: list[FunctionEvolutionEntry] = []

    def find_if_file_exists(sha: str) -> FindFunction | None:
        try:
            return get_target_function(repo_path, sha, file_path, target_fxn)
        except ValueError as exc:
            if isinstance(exc.__cause__, KeyError):
                return None  # The file did not exist at this revision.
            raise

    for commit in reversed(history.commits):
        parents = get_commit_details(repo_path, commit.sha).parent_shas
        previous_sha = parents[0] if parents else None

        if previous_sha is None:
            previous_function = None
            current_function = find_if_file_exists(commit.sha)
        else:
            try:
                comparison = get_function_comparison(
                    repo_path, previous_sha, commit.sha, file_path, target_fxn
                )
            except ValueError as exc:
                if not isinstance(exc.__cause__, KeyError):
                    raise
                previous_function = find_if_file_exists(previous_sha)
                current_function = find_if_file_exists(commit.sha)
            else:
                if comparison.has_changes:
                    entries.append(
                        FunctionEvolutionEntry(
                            commit_sha=commit.sha,
                            previous_sha=previous_sha,
                            function=comparison.function2,
                            changes=comparison.changes or ["Source changed"],
                            source_diff=comparison.source_diff,
                        )
                    )
                continue

        old_source = previous_function.source if previous_function else ""
        new_source = current_function.source if current_function else ""
        if old_source == new_source:
            continue
        changes = [
            f"Function '{target_fxn}' was {'added' if current_function else 'removed'}"
        ]
        source_diff = "".join(
            difflib.unified_diff(
                old_source.splitlines(keepends=True),
                new_source.splitlines(keepends=True),
                fromfile=previous_sha or "(no parent)",
                tofile=commit.sha,
            )
        )
        entries.append(
            FunctionEvolutionEntry(
                commit_sha=commit.sha,
                previous_sha=previous_sha,
                function=current_function,
                changes=changes,
                source_diff=source_diff,
            )
        )

    return FunctionEvolution(
        file_path=file_path,
        function_name=target_fxn,
        entries=entries,
        has_more=history.has_more,
    )
