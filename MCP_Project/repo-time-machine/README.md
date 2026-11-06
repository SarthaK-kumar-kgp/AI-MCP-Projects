# RepoTime Machine

RepoTime Machine is a read-only [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for exploring a local Git repository. It uses FastMCP for the server, GitPython for repository history, and CLDK for Python call graphs. The analysis lives in `src/repotime/analysis/`; `src/repotime/tools/` exposes it as MCP tools.

## Current status

Parts 2 and 3 are complete. Part 4 adds call graph queries and remains in progress. The server registers thirteen tools, one resource, and two resource templates. It supports repository history, historical file content, revision comparison, Python function evolution, dependencies, and possible change impact. The included stdio client exercises the Git tools and resources; the function and graph tools have been checked separately through an MCP client.

## Install and configure

Requires Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).

```sh
uv sync
export REPOSITORY_PATH=/absolute/path/to/a/git/repository
```

`REPOSITORY_PATH` must point to an existing local Git repository. The server reads this repository; it does not check out commits or change files. You can run the stdio server with `uv run repotime-server`. It waits for an MCP client on standard input and output, so it will appear idle if run alone in a terminal.

Run the included client with `uv run repotime-client`. It discovers tools and resources, uses commits and changed paths from the configured repository to call and read them, compares historical file snapshots, and checks expected errors. An empty repository skips history calls.

To check tool discovery and call a tool with arguments without configuring an external MCP host:

```sh
uv run python - <<'PY'
import asyncio
from fastmcp import Client
from repotime.server import mcp

async def main():
    async with Client(mcp) as client:
        print([tool.name for tool in await client.list_tools()])
        print(await client.call_tool("get_commit_list_tool", {"limit": 5, "offset": 0}))

asyncio.run(main())
PY
```

## Tools

| Tool | What it returns |
|---|---|
| `get_repository_name` | Configured repository name. |
| `get_repository_status` | Name, branch, and clean or dirty state. |
| `get_commit_summary_tool` | SHA, subject, and date for one commit. |
| `get_commit_list_tool` | A bounded page of commits. |
| `get_commit_details_tool` | Author, message, parents, and changed paths. |
| `get_file_history_tool` | Commits that changed one path; renames are not followed. |
| `get_file_content_tool` | UTF-8 file text at a commit, up to 1 MB. |
| `compare_revisions_tool` | Per-file status, line counts, and bounded patch text between two revisions. |
| `get_target_function_tool` | A Python function's source and location at one revision, or null if absent. |
| `get_function_comparison_tool` | Change categories and an exact source diff between two function versions. |
| `trace_function_evolution_tool` | Commits where a function changed, with a source diff for each change. |
| `get_functional_dependency_tool` | Direct and indirect functions called by a project function. |
| `get_change_impact_tool` | Direct and indirect callers that may be affected by a function change. |

History tools accept a `limit` and `offset`. Revision arguments can be commit SHAs or refs such as `HEAD`. The diff tool limits results to 100 files and 100,000 bytes of returned patch text. See [learning.md](learning.md) for the mistakes and fixes behind the implementation.

Function lookup accepts a qualified name such as `Cart.calculate`, or a short name when it is unambiguous. Evolution follows the same file path across commits, compares each commit to its first parent, and returns changes in chronological order within each bounded page. It does not follow renames or prove that a syntax change alters runtime behavior.

Graph tools accept a function identifier from the call graph, such as `shop.report.report_total`, plus optional `depth` (1–5) and `limit` (1–100). They build the graph from the configured repository when called. Direct and indirect results come from static call edges; `external` lists calls CLDK labels outside the analyzed source tree. Dynamic or unresolved calls may be missing, so impact means possible callers, not guaranteed breakage. The bundled client does not yet call these graph tools.

## Resources

| URI | What it returns |
|---|---|
| `repo://metadata` | Configured repository name, branch, and working-tree state as JSON. |
| `repo://commit/{sha}` | Commit details as JSON, for example `repo://commit/HEAD`. |
| `repo://file/{sha}/{path}` | UTF-8 file text at a revision, for example `repo://file/HEAD/src/shop/pricing.py`. Nested paths are supported. |

The file resource has the same 1 MB limit and path validation as the file-content tool. Missing revisions, missing files, and invalid paths return errors. Use a commit SHA when you need an immutable historical snapshot; `HEAD` follows the current branch.
