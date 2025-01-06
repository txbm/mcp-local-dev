"""MCP server implementation."""
import asyncio
import json
from typing import Dict, Any, List, cast

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.models import InitializationOptions
from mcp.server import stdio

from mcp_local_dev.environments.environment import (
    create_environment_from_github,
    create_environment_from_path,
    run_environment_tests,
    cleanup_environment,
    get_environment,
)
from mcp_local_dev.test_runners.execution import auto_run_tests
from mcp_local_dev.logging import configure_logging, get_logger

logger = get_logger("server")

tools = [
    types.Tool(
        name="local_dev_from_github",
        description="Create a new local development environment from a GitHub repository",
        inputSchema={
            "type": "object",
            "properties": {
                "github_url": {"type": "string", "description": "GitHub repository URL"}
            },
            "required": ["github_url"],
        },
    ),
    types.Tool(
        name="local_dev_from_filesystem",
        description="Create a new local development environment from a filesystem path",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Local filesystem path"}
            },
            "required": ["path"],
        },
    ),
    types.Tool(
        name="local_dev_run_tests",
        description="Auto-detect and run tests in a local development environment",
        inputSchema={
            "type": "object",
            "properties": {
                "env_id": {"type": "string", "description": "Environment identifier"}
            },
            "required": ["env_id"],
        },
    ),
    types.Tool(
        name="local_dev_cleanup",
        description="Clean up a local development environment",
        inputSchema={
            "type": "object",
            "properties": {
                "env_id": {"type": "string", "description": "Environment identifier"}
            },
            "required": ["env_id"],
        },
    ),
]


async def init_server() -> Server:
    logger.info(f"Registered tools: {', '.join(t.name for t in tools)}")

    server = Server("mcp-local-dev")

    server.setRequestHandler(
        "notifications/roots/list_changed",
        lambda: logger.debug("Roots list changed notification received")
    )

    server.setRequestHandler(
        "notifications/initialized", 
        lambda: logger.debug("Initialized notification received")
    )

    @server.list_tools()
    async def list_tools() -> List[types.Tool]:
        logger.debug("Tools requested")
        return tools

    @server.call_tool()
    async def call_tool(
        name: str, arguments: Dict[str, Any]
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        try:
            logger.debug(f"Tool call received: {name} with arguments {arguments}")
            
            if name == "local_dev_from_github":
                logger.debug("Creating environment from GitHub")
                env = await create_environment_from_github(arguments["github_url"])
                result = {
                    "success": True,
                    "data": {
                        "id": env.id,
                        "working_dir": str(env.sandbox.work_dir),
                        "created_at": env.created_at.isoformat(),
                        "runtime": env.runtime_config.name.value,
                    }
                }
                logger.debug(f"Environment created successfully: {result}")
                return [types.TextContent(type="text", text=json.dumps(result))]
                
            elif name == "local_dev_from_filesystem":
                env = await create_environment_from_path(arguments["path"])
                return [types.TextContent(type="text", text=json.dumps({
                    "success": True,
                    "data": {
                        "id": env.id,
                        "working_dir": str(env.sandbox.work_dir),
                        "created_at": env.created_at.isoformat(),
                        "runtime": env.runtime_config.name.value,
                    }
                }))]
                
            elif name == "local_dev_run_tests":
                env = get_environment(arguments["env_id"])
                if not env:
                    return [types.TextContent(type="text", text=json.dumps({
                        "success": False,
                        "error": f"Unknown environment: {arguments['env_id']}"
                    }))]
                return cast(
                    list[types.TextContent | types.ImageContent | types.EmbeddedResource],
                    await run_environment_tests(env),
                )

            elif name == "local_dev_cleanup":
                env = get_environment(arguments["env_id"])
                if not env:
                    return [types.TextContent(type="text", text=json.dumps({
                        "success": False,
                        "error": f"Unknown environment: {arguments['env_id']}"
                    }))]
                cleanup_environment(env)
                return [types.TextContent(type="text", text=json.dumps({
                    "success": True,
                    "data": {"message": "Environment cleaned up successfully"}
                }))]

            return [types.TextContent(type="text", text=json.dumps({
                "success": False,
                "error": f"Unknown tool: {name}"
            }))]

        except Exception as e:
            return [types.TextContent(type="text", text=json.dumps({
                "success": False,
                "error": str(e)
            }))]

    @server.progress_notification()
    async def handle_progress(
        progress_token: str | int, progress: float, total: float | None = None
    ) -> None:
        """Handle progress notifications."""
        logger.debug(f"Progress notification: {progress}/{total if total else '?'}")

    return server


async def serve() -> None:
    configure_logging()
    logger.info("Starting MCP runtime server")
    server = await init_server()
    async with stdio.stdio_server() as (read_stream, write_stream):
        init_options = InitializationOptions(
            server_name="mcp-local-dev",
            server_version="0.1.0",
            capabilities=types.ServerCapabilities(
                tools=types.ToolsCapability(listChanged=False),
                logging=types.LoggingCapability(),
            ),
        )
        await server.run(read_stream, write_stream, init_options)

def main() -> None:
    """Run the MCP server."""
    asyncio.run(serve())
