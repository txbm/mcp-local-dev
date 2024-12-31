"""MCP server implementation."""
import asyncio
import json
import logging
import signal
import sys
from typing import Dict, Any, List, Union, Optional

import mcp.types as types
from mcp.server.lowlevel import Server, NotificationRegistry
from mcp.server.models import InitializationOptions
from mcp.server import stdio

from mcp_runtime_server.environments import (
    create_environment,
    cleanup_environment,
    ENVIRONMENTS,
)
from mcp_runtime_server.testing.execution import auto_run_tests
from mcp_runtime_server.types import EnvironmentConfig
from mcp_runtime_server.logging import configure_logging, get_logger

logger = get_logger("server")

tools = [
    types.Tool(
        name="create_environment",
        description="Create a new runtime environment with sandbox isolation",
        inputSchema={
            "type": "object",
            "properties": {
                "github_url": {"type": "string", "description": "GitHub repository URL"}
            },
            "required": ["github_url"],
        },
    ),
    types.Tool(
        name="run_tests",
        description="Auto-detect and run tests in a sandboxed environment",
        inputSchema={
            "type": "object",
            "properties": {
                "env_id": {"type": "string", "description": "Environment identifier"}
            },
            "required": ["env_id"],
        },
    ),
    types.Tool(
        name="cleanup",
        description="Clean up a sandboxed environment",
        inputSchema={
            "type": "object", 
            "properties": {
                "env_id": {"type": "string", "description": "Environment identifier"}
            },
            "required": ["env_id"],
        },
    ),
]

def initialize_notification_registry() -> NotificationRegistry:
    """Initialize and configure the notification registry."""
    registry = NotificationRegistry()

    @registry.register("notifications/initialized")
    async def handle_initialized(params: Dict[str, Any]) -> None:
        logger.debug("Initialized notification")
        # No response needed

    @registry.register("notifications/progress")
    async def handle_progress(params: Dict[str, Any]) -> None:
        logger.debug("Progress notification")
        # No response needed

    @registry.register("notifications/roots/list_changed")
    async def handle_roots_list_changed(params: Dict[str, Any]) -> None:
        logger.debug("Roots list changed notification")
        # No response needed

    return registry

async def init_server() -> Server:
    logger.info(f"Registered tools: {', '.join(t.name for t in tools)}")
    
    server = Server("mcp-runtime-server")
    server.notification_registry = initialize_notification_registry()

    @server.list_tools()
    async def list_tools() -> List[types.Tool]:
        logger.debug("Tools requested")
        return tools

    @server.call_tool()
    async def call_tool(
        name: str, arguments: Dict[str, Any]
    ) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        try:
            logger.debug(f"Tool called: {name} with args: {arguments}")
            
            if name == "create_environment":
                config = EnvironmentConfig(github_url=arguments["github_url"])
                env = await create_environment(config)
                result = {
                    "id": env.id,
                    "working_dir": str(env.work_dir),
                    "created_at": env.created_at.isoformat(),
                    "runtime": env.manager.value if env.manager else None,
                }
                return [types.TextContent(text=json.dumps(result), type="text")]

            elif name == "run_tests":
                if arguments["env_id"] not in ENVIRONMENTS:
                    return [types.TextContent(
                        text=json.dumps({
                            "success": False,
                            "error": f"Unknown environment: {arguments['env_id']}"
                        }),
                        type="text"
                    )]

                env = ENVIRONMENTS[arguments["env_id"]]
                if not env.manager:
                    return [types.TextContent(
                        text=json.dumps({
                            "success": False,
                            "error": "Runtime not detected for environment"
                        }),
                        type="text"
                    )]

                return await auto_run_tests(env)

            elif name == "cleanup":
                cleanup_environment(arguments["env_id"])
                return [types.TextContent(
                    text=json.dumps({"success": True}),
                    type="text"
                )]

            return [types.TextContent(
                text=json.dumps({
                    "success": False,
                    "error": f"Unknown tool: {name}"
                }),
                type="text"
            )]

        except Exception as e:
            logger.exception(f"Tool invocation failed: {str(e)}")
            return [types.TextContent(
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }),
                type="text"
            )]

    return server

async def cleanup_all_environments():
    for env_id in list(ENVIRONMENTS.keys()):
        try:
            cleanup_environment(env_id)
        except Exception as e:
            logger.error(f"Failed to cleanup environment {env_id}: {e}")

async def serve() -> None:
    configure_logging()
    logger.info("Starting MCP runtime server")

    server = await init_server()
    try:
        async with stdio.stdio_server() as (read_stream, write_stream):
            init_options = InitializationOptions(
                server_name="mcp-runtime-server",
                server_version="0.1.0",
                capabilities=types.ServerCapabilities(
                    tools=types.ToolsCapability(listChanged=False),
                    notifications=types.NotificationsCapability(
                        initialized=True,
                        progress=True,
                        roots=types.RootsCapability(listChanged=True)
                    )
                )
            )
            await server.run(read_stream, write_stream, init_options)
    except asyncio.CancelledError:
        logger.info("Server shutdown initiated")
        await cleanup_all_environments()
    except Exception as e:
        logger.exception("Server error")
        await cleanup_all_environments()
        raise
    finally:
        await cleanup_all_environments()

def handle_shutdown(signum, frame):
    logger.info(f"Shutting down on signal {signum}")
    sys.exit(0)

def setup_handlers() -> None:
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

def main() -> None:
    setup_handlers()
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception:
        logger.exception("Fatal server error")
        sys.exit(1)