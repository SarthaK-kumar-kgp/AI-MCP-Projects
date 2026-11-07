"""Exercise RepoTime Machine tools through a stdio MCP connection."""

import asyncio
import json
import logging
import os
import sys
from urllib.parse import quote

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("repo-time-machine-client")


async def call_and_show(client: Client, name: str, arguments: dict | None = None) -> dict:
    """Call a tool and show a short preview of its structured result."""
    result = await client.call_tool(name, arguments)
    data = result.structured_content or {}
    print(f"{name}: {json.dumps(data, default=str)[:500]}")
    return data


async def show_discovery(client: Client) -> None:
    """Show the tools and resources this server offers."""
    print("\n=== Discovered Tools ===")
    for tool in await client.list_tools():
        print(f"{tool.name}: {tool.description}")
        print(f"Input schema: {json.dumps(tool.input_schema, indent=2)}")

    print("\n=== Discovered Resources ===")
    print([str(resource.uri) for resource in await client.list_resources()])
    print([str(template.uri_template) for template in await client.list_resource_templates()])


async def check_repository_metadata(client: Client) -> None:
    """Compare repository status from a tool and a resource."""
    await call_and_show(client, "get_repository_name")
    status = await call_and_show(client, "get_repository_status")
    metadata = json.loads((await client.read_resource("repo://metadata"))[0].text)
    if metadata != status:
        raise RuntimeError("Metadata resource disagrees with repository status tool")
    print("repo://metadata matches get_repository_status")


async def check_file_snapshots(client: Client, changes: list[dict], older_sha: str, latest_sha: str) -> None:
    """Find a readable file that differs between two commits."""
    for change in changes:
        if (
            change["change_type"] != "M"
            or change["old_path"] != change["new_path"]
            or not (change["additions"] or change["deletions"])
        ):
            continue
        path = quote(change["new_path"], safe="/")
        try:
            old_text = (await client.read_resource(f"repo://file/{older_sha}/{path}"))[0].text
            new_text = (await client.read_resource(f"repo://file/{latest_sha}/{path}"))[0].text
        except Exception:
            continue  # A modified file may be binary or exceed the text limit.
        if old_text != new_text:
            print(f"File resource differs across commits: {change['new_path']}")
            return
    print("No readable modified file was available at both commits.")


async def check_changed_file(client: Client, candidates: list[tuple[str, str]]) -> None:
    """Read one changed text file through both its tool and resource."""
    if not candidates:
        return

    await call_and_show(
        client,
        "get_file_history_tool",
        {"file_path": candidates[0][0], "limit": 2, "offset": 0},
    )
    for file_path, commit_sha in candidates[:10]:
        result = await client.call_tool(
            "get_file_content_tool",
            {"file_path": file_path, "commit_sha": commit_sha},
            raise_on_error=False,
        )
        if result.is_error:
            continue
        content = result.structured_content["content"]
        print(f"get_file_content_tool: {file_path} at {commit_sha[:7]} ({len(content)} characters)")
        uri = f"repo://file/{commit_sha}/{quote(file_path, safe='/')}"
        resource_text = (await client.read_resource(uri))[0].text
        if resource_text != content:
            raise RuntimeError("File resource disagrees with file content tool")
        print(f"{uri} matches get_file_content_tool")
        return
    print("No changed file was available as UTF-8 text.")


async def inspect_recent_commits(client: Client) -> None:
    """Use recent commit SHAs and paths to inspect Git history."""
    commit_page = await call_and_show(client, "get_commit_list_tool", {"limit": 2, "offset": 0})
    commits = commit_page["commits"]
    if not commits:
        print("Repository has no commits; skipping history and diff tools.")
        return

    latest_sha = commits[0]["sha"]
    await call_and_show(client, "get_commit_summary_tool", {"commit_sha": latest_sha})
    details = await call_and_show(client, "get_commit_details_tool", {"commit_sha": latest_sha})
    commit_resource = json.loads((await client.read_resource(f"repo://commit/{latest_sha}"))[0].text)
    if commit_resource != details:
        raise RuntimeError("Commit resource disagrees with commit details tool")
    print(f"repo://commit/{latest_sha} matches get_commit_details_tool")

    candidates = [(path, latest_sha) for path in details["changed_files"]]
    if len(commits) > 1:
        older_sha = commits[1]["sha"]
        comparison = await call_and_show(
            client, "compare_revisions_tool", {"old_sha": older_sha, "new_sha": latest_sha}
        )
        changes = comparison["files"]
        await check_file_snapshots(client, changes, older_sha, latest_sha)
        candidates = [
            (change["new_path"], latest_sha)
            if change["new_path"]
            else (change["old_path"], older_sha)
            for change in changes
        ] or candidates

    await check_changed_file(client, candidates)


async def check_expected_errors(client: Client) -> None:
    """Confirm that known bad requests fail cleanly."""
    print("\n=== Testing Error Handling ===")
    invalid_revision = await client.call_tool(
        "get_commit_details_tool",
        {"commit_sha": "definitely-not-a-commit"},
        raise_on_error=False,
    )
    if not invalid_revision.is_error:
        raise RuntimeError("Invalid revision unexpectedly succeeded")
    print("Invalid revision returned a controlled tool error.")

    for uri in (
        "repo://commit/definitely-not-a-commit",
        "repo://file/HEAD/missing-file.py",
        "repo://file/HEAD/../outside.py",
    ):
        try:
            await client.read_resource(uri)
        except Exception:
            print(f"Invalid resource was rejected: {uri}")
        else:
            raise RuntimeError(f"Invalid resource unexpectedly succeeded: {uri}")

    try:
        await client.call_tool("non_existent_tool_name")
    except Exception as exc:
        print(f"Unknown tool returned an expected error: {exc}")
    else:
        raise RuntimeError("Unknown tool unexpectedly succeeded")


async def run_client() -> None:
    """Connect once, then run the existing discovery and Git checks."""
    repository_path = os.getenv("REPOSITORY_PATH")
    server_env = {"REPOSITORY_PATH": repository_path} if repository_path else None

    logger.info("Connecting to the RepoTime Machine server...")
    async with Client(StdioTransport(command="repotime-server", args=[], env=server_env)) as client:
        await show_discovery(client)
        print("\n=== Calling Active Tools ===")
        await check_repository_metadata(client)
        await inspect_recent_commits(client)
        await check_expected_errors(client)
    logger.info("Disconnected safely.")


def main() -> None:
    try:
        asyncio.run(run_client())
    except Exception as exc:
        logger.error("Client failed: %s", exc)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
