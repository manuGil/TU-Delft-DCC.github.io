"""
MCP server for an AI agent that helps users to find information 
on the DCC guides.
"""

import asyncio
import os
import signal
import sys
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("agent", "An AI agent that helps users to find information on the DCC guides.")


@mcp.tool()
def greet_user(name: str) -> str:
    """Greets the user with their name."""
    return f"Hello, {name}! How can I assist you with the DCC guides today?"


async def run_server():
    """Run the MCP server with proper signal handling."""
    loop = asyncio.get_running_loop()
    
    def handle_signal():
        print("\nShutting down DCC guides agent MCP server...", file=sys.stderr)
        # Force exit to avoid blocking on stdin
        os._exit(0)

    # Add signal handlers for graceful shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    print("Started the DCC guides agent MCP server...", file=sys.stderr)
    print("Press Ctrl+C to stop the server", file=sys.stderr)

    await mcp.run_stdio_async()


def main():
    asyncio.run(run_server())

if __name__ == "__main__":
    main()

