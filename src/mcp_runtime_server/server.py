"""MCP server implementation."""

import asyncio
import json
import logging
import signal
import sys
from typing import Dict, Any, List, Union

from mcp.server.lowlevel import Server
from mcp.types import Tool, TextContent
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

def init_server() -> Server:
    logger.debug("Initializing MCP runtime server")
    server = Server("mcp-runtime-server")

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        tools = [
            Tool(
                name="create_environment",
                description="Create a new runtime environment with sandbox isolation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "github_url": {
                            "type": "string",
                            "description": "GitHub repository URL",
                        }
                    },
                    "required": ["github_url"],
                },
            ),
            Tool(
                name="run_tests",
                description="Auto-detect and run tests in a sandboxed environment",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "env_id": {
                            "type": "string",
                            "description": "Environment identifier",
                        }
                    },
                    "required": ["env_id"],
                },
            ),
            Tool(
                name="cleanup",
                description="Clean up a sandboxed environment",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "env_id": {
                            "type": "string",
                            "description": "Environment identifier",
                        }
                    },
                    "required": ["env_id"],
                },
            ),
        ]
        logger.debug(f"Found {len(tools)} available tools")
        return tools

    @server.call_tool()
    async def call_tool(
        name: str, arguments: Dict[str, Any]
    ) -> List[Union[TextContent]]:
        try:
            logger.debug(
                "Tool invocation started",
                extra={"tool": name, "arguments": arguments}
            )

            if name == "create_environment":
                config = EnvironmentConfig(github_url=arguments["github_url"])
                env = await create_environment(config)
                result = {
                    "id": env.id,
                    "working_dir": str(env.work_dir),
                    "created_at": env.created_at.isoformat(),
                    "runtime": env.manager.value if env.manager else None,
                }
                return [TextContent(type="text", text=json.dumps(result))]

            elif name == "run_tests":
                if arguments["env_id"] not in ENVIRONMENTS:
                    raise RuntimeError(f"Unknown environment: {arguments['env_id']}")

                env = ENVIRONMENTS[arguments["env_id"]]
                if not env.manager:
                    raise RuntimeError("Runtime not detected for environment")

                results = await auto_run_tests(env)
                return [TextContent(type="text", text=json.dumps(results))]

            elif name == "cleanup":
                cleanup_environment(arguments["env_id"])
                return [TextContent(type="text", text=json.dumps({"status": "success"}))]

            raise RuntimeError(f"Unknown tool: {name}")

        except Exception as e:
            logger.exception(
                "Tool invocation failed",
                extra={
                    "tool": name,
                    "arguments": arguments,
                    "error": str(e)
                }
            )
            return [TextContent(type="text", text=str(e))]

    return server

async def cleanup_all_environments():
    """Clean up all environments."""
    for env_id in list(ENVIRONMENTS.keys()):
        try:
            cleanup_environment(env_id)
        except Exception as e:
            logger.error(f"Failed to cleanup environment {env_id}: {e}")

def setup_handlers() -> None:
    def handle_shutdown(signum, frame):
        logger.info(f"Shutting down on signal {signum}")
        cleanup_all_environments()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

async def serve() -> None:
    configure_logging()
    logger.info("Starting MCP runtime server")

    server = init_server()
    setup_handlers()

    try:
        async with stdio.stdio_server() as (read_stream, write_stream):
            options = server.create_initialization_options()
            await server.run(read_stream, write_stream, options)
    except Exception as e:
        logger.exception("Server error")
        await cleanup_all_environments()
        raise
    finally:
        await cleanup_all_environments()

def main() -> None:
    asyncio.run(serve())