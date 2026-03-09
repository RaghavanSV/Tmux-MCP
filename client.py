"""
MCP Test Client for the Post-Exploitation tmux MCP Server.

An interactive REPL that connects to server.py via stdio transport,
lists available tools, and lets you call them manually.

Usage:
    python client.py
"""

import asyncio
import json
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


SERVER_SCRIPT = "server.py"


async def main():
    stack = AsyncExitStack()
    params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_SCRIPT],
    )

    print("⏳ Connecting to MCP server...")
    transport = await stack.enter_async_context(stdio_client(params))
    read_stream, write_stream = transport
    session: ClientSession = await stack.enter_async_context(
        ClientSession(read_stream, write_stream)
    )
    await session.initialize()
    print("✅ Connected!\n")

    # Fetch and display available tools
    tools_response = await session.list_tools()
    tools = {t.name: t for t in tools_response.tools}

    print("=" * 50)
    print(f"  Available Tools ({len(tools)})")
    print("=" * 50)
    for name, tool in tools.items():
        params_list = []
        if tool.inputSchema and "properties" in tool.inputSchema:
            required = tool.inputSchema.get("required", [])
            for pname, pinfo in tool.inputSchema["properties"].items():
                req = "*" if pname in required else ""
                params_list.append(f"{pname}{req}")
        params_str = ", ".join(params_list) if params_list else "(none)"
        print(f"  {name}({params_str})")
    print("=" * 50)
    print("\nType a tool name to call it, 'list' to see tools, or 'quit' to exit.\n")

    # Interactive REPL
    while True:
        try:
            tool_name = input("tool> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not tool_name:
            continue
        if tool_name.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break
        if tool_name.lower() == "list":
            for name in tools:
                print(f"  {name}")
            continue

        if tool_name not in tools:
            print(f"  ❌ Unknown tool: {tool_name}")
            continue

        # Build arguments from tool schema
        tool = tools[tool_name]
        args = {}
        if tool.inputSchema and "properties" in tool.inputSchema:
            required = tool.inputSchema.get("required", [])
            for pname, pinfo in tool.inputSchema["properties"].items():
                ptype = pinfo.get("type", "string")
                default = pinfo.get("default")
                is_req = pname in required

                if default is not None:
                    prompt_str = f"  {pname} ({ptype}, default={default}): "
                elif is_req:
                    prompt_str = f"  {pname} ({ptype}, required): "
                else:
                    prompt_str = f"  {pname} ({ptype}, optional): "

                val = input(prompt_str).strip()

                if not val:
                    if is_req:
                        print(f"  ❌ {pname} is required.")
                        break
                    continue  # skip optional with no input

                # Type coercion
                if ptype == "integer":
                    try:
                        val = int(val)
                    except ValueError:
                        print(f"  ❌ {pname} must be an integer.")
                        break
                elif ptype == "boolean":
                    val = val.lower() in ("true", "1", "yes")

                args[pname] = val
            else:
                # for-else: only runs if loop completed without break
                pass

        # Call the tool
        print(f"\n  ⏳ Calling {tool_name}...")
        try:
            result = await session.call_tool(tool_name, args)
            for content in result.content:
                if hasattr(content, "text"):
                    try:
                        data = json.loads(content.text)
                        print(f"  ✅ Result:\n{json.dumps(data, indent=2)}")
                    except json.JSONDecodeError:
                        print(f"  ✅ Result:\n{content.text}")
                else:
                    print(f"  ✅ Result: {content}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        print()

    await stack.aclose()


if __name__ == "__main__":
    asyncio.run(main())
