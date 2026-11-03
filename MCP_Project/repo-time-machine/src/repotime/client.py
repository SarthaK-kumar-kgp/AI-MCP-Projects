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


async def run_client() -> None:
    repository_path = os.getenv("REPOSITORY_PATH")
    server_env = {"REPOSITORY_PATH": repository_path} if repository_path else None

    logger.info("Connecting to the RepoTime Machine server...")
    async with Client(StdioTransport(command="repotime-server", args=[], env=server_env)) as client:
        print("\n=== Discovered Tools ===")
        for tool in await client.list_tools():
            print(f"{tool.name}: {tool.description}")
            print(f"Input schema: {json.dumps(tool.input_schema, indent=2)}")

        print("\n=== Discovered Resources ===")
        print([str(resource.uri) for resource in await client.list_resources()])
        print([str(template.uri_template) for template in await client.list_resource_templates()])

        print("\n=== Calling Active Tools ===")
        await call_and_show(client, "get_repository_name")
        status = await call_and_show(client, "get_repository_status")
        metadata = json.loads((await client.read_resource("repo://metadata"))[0].text)
        if metadata != status:
            raise RuntimeError("Metadata resource disagrees with repository status tool")
        print("repo://metadata matches get_repository_status")
        commit_page = await call_and_show(
            client, "get_commit_list_tool", {"limit": 2, "offset": 0}
        )
        commits = commit_page["commits"]

        if commits:
            latest_sha = commits[0]["sha"]
            await call_and_show(
                client, "get_commit_summary_tool", {"commit_sha": latest_sha}
            )
            details = await call_and_show(
                client, "get_commit_details_tool", {"commit_sha": latest_sha}
            )
            commit_resource = json.loads(
                (await client.read_resource(f"repo://commit/{latest_sha}"))[0].text
            )
            if commit_resource != details:
                raise RuntimeError("Commit resource disagrees with commit details tool")
            print(f"repo://commit/{latest_sha} matches get_commit_details_tool")
            file_candidates = [
                (path, latest_sha) for path in details["changed_files"]
            ]

            if len(commits) > 1:
                older_sha = commits[1]["sha"]
                comparison = await call_and_show(
                    client,
                    "compare_revisions_tool",
                    {"old_sha": older_sha, "new_sha": latest_sha},
                )
                for change in comparison["files"]:
                    if (
                        change["change_type"] != "M"
                        or change["old_path"] != change["new_path"]
                        or not (change["additions"] or change["deletions"])
                    ):
                        continue
                    path = quote(change["new_path"], safe="/")
                    try:
                        old_text = (
                            await client.read_resource(f"repo://file/{older_sha}/{path}")
                        )[0].text
                        new_text = (
                            await client.read_resource(f"repo://file/{latest_sha}/{path}")
                        )[0].text
                    except Exception:
                        continue  # A modified file may be binary or exceed the text limit.
                    if old_text != new_text:
                        print(f"File resource differs across commits: {change['new_path']}")
                        break
                else:
                    print("No readable modified file was available at both commits.")
                file_candidates = [
                    (change["new_path"], latest_sha)
                    if change["new_path"]
                    else (change["old_path"], older_sha)
                    for change in comparison["files"]
                ] or file_candidates

            if file_candidates:
                await call_and_show(
                    client,
                    "get_file_history_tool",
                    {"file_path": file_candidates[0][0], "limit": 2, "offset": 0},
                )
                for file_path, commit_sha in file_candidates[:10]:
                    result = await client.call_tool(
                        "get_file_content_tool",
                        {"file_path": file_path, "commit_sha": commit_sha},
                        raise_on_error=False,
                    )
                    if not result.is_error:
                        content = result.structured_content["content"]
                        print(
                            f"get_file_content_tool: {file_path} at "
                            f"{commit_sha[:7]} ({len(content)} characters)"
                        )
                        uri = f"repo://file/{commit_sha}/{quote(file_path, safe='/')}"
                        resource_text = (await client.read_resource(uri))[0].text
                        if resource_text != content:
                            raise RuntimeError("File resource disagrees with file content tool")
                        print(f"{uri} matches get_file_content_tool")
                        break
                else:
                    print("No changed file was available as UTF-8 text.")
        else:
            print("Repository has no commits; skipping history and diff tools.")

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

    logger.info("Disconnected safely.")


def main() -> None:
    try:
        asyncio.run(run_client())
    except Exception as exc:
        logger.error("Client failed: %s", exc)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
