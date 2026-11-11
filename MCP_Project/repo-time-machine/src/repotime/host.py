import asyncio
import json
import os
from typing import Any

from dotenv import load_dotenv
from fastmcp import Client
from openai import OpenAI

load_dotenv()

DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL")
deepseek_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL")
)


def _parse_json(content: str) -> dict[str, Any]:
    """Read a model's tool arguments as one JSON object."""
    arguments = json.loads(content)
    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be a JSON object")
    return arguments


async def get_all_tools(client: Client) -> list[dict[str, Any]]:
    """Return a list of all tools available in the client."""
    response = await client.list_tools()
    available_tools =[
        {"type":"function",
         "function" :{
        "name":tool.name,
        "description":tool.description,
        "parameters":tool.input_schema
    }} for tool in response]
    return available_tools

async def get_all_prompts(client: Client) -> list[dict[str, Any]]:
    """List prompt names and arguments; retrieving a prompt is a separate step."""
    return [
            {
            "type":"prompt",
            "prompt": {
            "name": prompt.name,
            "description": prompt.description,
            "arguments" :[argument.model_dump() for argument in (prompt.arguments or [])],
            }} for prompt in await client.list_prompts()
    ]


async def process_query(query: str, llm_client: OpenAI, client: Client) -> str:
    """Answer a question by letting DeepSeek call the connected MCP server."""
    available_tools = await get_all_tools(client)
    tool_names = {tool["function"]["name"] for tool in available_tools}
    has_tool_evidence = False
    unresolved_tool_errors: set[str] = set()
    messages = [
        {
            "role": "system",
            "content": (
                "Use the available repository tools to answer questions about code and Git history. "
                "Support factual claims with returned file paths and commit SHAs. "
                "Do not treat failed tool calls as evidence. "
                "If the tools do not provide enough evidence, say what is missing."
            ),
        },
        {"role": "user", "content": query},
    ]

    for _ in range(8):
        response = await asyncio.to_thread(
            llm_client.chat.completions.create,
            model=DEEPSEEK_MODEL,
            messages=messages,
            temperature=0.2,
            tools=available_tools,
            max_tokens=1000,
            extra_body={"thinking": {"type": "disabled"}},
        )
        message = response.choices[0].message
        if not message.tool_calls:
            if not message.content:
                raise RuntimeError("DeepSeek returned neither an answer nor a tool call")
            if unresolved_tool_errors:
                names = ", ".join(sorted(unresolved_tool_errors))
                return f"I couldn't verify an answer because these tool requests were not resolved: {names}."
            if not has_tool_evidence:
                return "I couldn't verify an answer because no repository tool completed successfully."
            return message.content.strip()

        messages.append(message)
        for tool_call in message.tool_calls:
            name = tool_call.function.name
            try:
                if name not in tool_names:
                    raise ValueError(f"Unknown tool: {name}")
                arguments = _parse_json(tool_call.function.arguments)
            except ValueError as exc:
                unresolved_tool_errors.add(name)
                tool_output = {"is_error": True, "result": str(exc)}
            else:
                result = await client.call_tool(name, arguments, raise_on_error=False)
                if result.is_error:
                    return f"I couldn't verify the answer because {name} failed. Check the server error and try again."
                unresolved_tool_errors.discard(name)
                has_tool_evidence = True
                tool_output = {
                    "is_error": result.is_error,
                    "result": (
                        result.structured_content
                        if result.structured_content is not None
                        else [block.model_dump(mode="json") for block in result.content]
                    ),
                }
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_output),
                }
            )

    raise RuntimeError("DeepSeek requested too many rounds of tool calls")
