import asyncio
import json
import logging
import os
import sys
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

# Setup standard logging to stderr
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("repo-time-machine-client")

async def run_client():
    logger.info("Connecting to the RepoTime Machine server...")
    repository_path = os.getenv("REPOSITORY_PATH")
    server_env = {"REPOSITORY_PATH": repository_path} if repository_path is not None else None
    
    # 1. Point FastMCP directly to your server command. 
    # This automatically spawns the child process and handles the protocol setup under the hood.
    async with Client(StdioTransport(command="repotime-server", args=[], env=server_env)) as client:
        
        # 2. Discover available tools
        print("\n=== Discovered Tools ===")
        # client.list_tools() returns a clean list of tool objects directly
        for tool in await client.list_tools():
            print(f"Tool Name: {tool.name}")
            print(f"Description: {tool.description}")
            print(f"Input schema: {json.dumps(tool.input_schema, indent=2)}")
            print("-" * 30)
            
        # 3. Call Valid Tools
        print("\n=== Calling Active Tools ===")
        try:
            # call_tool lets you just pass the name string. 
            # If there are no arguments, you can omit the arguments parameter entirely or pass empty keywords!
            for tool in await client.list_tools():
                logger.info(f"Calling tool: {tool.name}")
                result = await client.call_tool(tool.name)
                print(f"{tool.name} output: {result}")
            # name_result = client.call_tool("get_repository_name")
            # print(f"get_repository_name output: {name_result}")
            
            # status_result = client.call_tool("get_repository_status")
            # print(f"get_repository_status output: {status_result}")
            
        except Exception as e:
            logger.error(f"Failed during tool execution: {e}")
            raise
            
        # 4. Test Error Handling
        print("\n=== Testing Error Handling ===")
        try:
            logger.info("Attempting an invalid tool...")
            await client.call_tool("non_existent_tool_name")
        except Exception as e:
            print(f"Successfully caught expected error: {e}")

    # Exiting the 'with' block automatically disconnects and kills the server child process.
    logger.info("Disconnected safely.")

def main() -> None:
    try:
        asyncio.run(run_client())
    except Exception as exc:
        logger.error("Client failed: %s", exc)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
