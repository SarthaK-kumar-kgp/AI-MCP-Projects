# RepoTime Machine

RepoTime Machine is a read-only [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for exploring a local Git repository. It uses FastMCP for the server and GitPython for repository history. The Git analysis lives in `src/repotime/analysis/`; `src/repotime/tools/` exposes it as MCP tools.

## Current status

The server registers eight tools. Repository status, commit history, historical file content, and revision comparison are implemented. Part 2 is still in progress: repository resources and a complete stdio client check remain. The current `repotime-client` discovers tools but then calls every tool without arguments, so it fails when it reaches a tool that requires a SHA or file path.

## Install and configure

Requires Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).

```sh
uv sync
export REPOSITORY_PATH=/absolute/path/to/a/git/repository
```

`REPOSITORY_PATH` must point to an existing local Git repository. The server reads this repository; it does not check out commits or change files. You can run the stdio server with `uv run repotime-server`. It waits for an MCP client on standard input and output, so it will appear idle if run alone in a terminal.

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

History tools accept a `limit` and `offset`. Revision arguments can be commit SHAs or refs such as `HEAD`. The diff tool limits results to 100 files and 100,000 bytes of returned patch text. See [learning.md](learning.md) for the mistakes and fixes behind the implementation.
