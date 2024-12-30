"""MCP server implementation."""
import asyncio
import json
import logging
import signal
import sys
import traceback
from typing import Dict, Any, List, Union

from mcp.server.lowlevel import Server
from mcp.types import Tool, TextContent
from mcp.server import stdio

from mcp_runtime_server.runtime import create_environment, cleanup_environment, run_command, ENVIRONMENTS
from mcp_runtime_server.testing import auto_run_tests
from mcp_runtime_server.types import RuntimeConfig
from mcp_runtime_server.logging import configure_logging, log_with_data

logger = logging.getLogger(__name__)


def init_server() -> Server:
    """Initialize the MCP runtime server."""
    logger.debug("Initializing MCP runtime server")
    server = Server("mcp-runtime-server")

    @server.list_tools() 
    async def list_tools() -> List[Tool]:
        """List available runtime management tools."""
        logger.debug("Listing available tools")
        tools = [
            Tool(
                name="create_environment",
                description="Create a new runtime environment with sandbox isolation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "manager": {
                            "type": "string", 
                            "enum": ["node", "bun", "uv"],
                            "description": "Runtime manager to use"
                        },
                        "github_url": {
                            "type": "string", 
                            "description": "GitHub repository URL"
                        }
                    },
                    "required": ["manager", "github_url"]
                }
            ),
            Tool(
                name="run_tests",
                description="Auto-detect and run tests in a sandboxed environment",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "env_id": {
                            "type": "string",
                            "description": "Environment identifier"
                        }
                    },
                    "required": ["env_id"]
                }
            ),
            Tool(
                name="cleanup",
                description="Clean up a sandboxed environment",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "env_id": {
                            "type": "string",
                            "description": "Environment identifier"
                        }
                    },
                    "required": ["env_id"]
                }
            )
        ]
        logger.debug(f"Found {len(tools)} available tools")
        return tools

    @server.call_tool()
    async def call_tool(
        name: str, 
        arguments: Dict[str, Any]
    ) -> List[Union[TextContent]]:
        """Handle tool invocations."""
        try:
            log_with_data(logger, logging.DEBUG, f"Tool invocation started: {name}", {
                "tool": name,
                "arguments": arguments
            })

            if name == "create_environment":
                config = RuntimeConfig(
                    manager=arguments["manager"],
                    github_url=arguments["github_url"]
                )
                env = await create_environment(config)
                result = {
                    "id": env.id,
                    "working_dir": str(env.work_dir),
                    "created_at": env.created_at.isoformat()
                }
                
                log_with_data(logger, logging.DEBUG, "Environment created successfully", result)
                return [TextContent(type="text", text=json.dumps(result))]

            elif name == "run_tests":
                if "env_id" not in arguments:
                    logger.error("Missing env_id parameter")
                    raise RuntimeError("Missing env_id parameter")

                if arguments["env_id"] not in ENVIRONMENTS:
                    logger.error(f"Unknown environment: {arguments['env_id']}")
                    raise RuntimeError(f"Unknown environment: {arguments['env_id']}")

                log_with_data(logger, logging.DEBUG, "Running tests", {"env_id": arguments["env_id"]})

                results = await auto_run_tests(ENVIRONMENTS[arguments["env_id"]])
                log_with_data(logger, logging.DEBUG, "Test execution completed", results)
                
                return [TextContent(type="text", text=json.dumps(results))]

            elif name == "cleanup":
                if "env_id" not in arguments:
                    logger.error("Missing env_id parameter")
                    raise RuntimeError("Missing env_id parameter")
                
                log_with_data(logger, logging.DEBUG, "Cleaning up environment", {
                    "env_id": arguments["env_id"]
                })
                    
                await cleanup_environment(arguments["env_id"])
                return [TextContent(type="text", text=json.dumps({"status": "success"}))]

            logger.error(f"Unknown tool requested: {name}")
            raise RuntimeError(f"Unknown tool: {name}")
            
        except Exception as e:
            logger.error(
                "Error occurred",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                    "tool": name,
                    "arguments": arguments
                }
            )
            logger.error("Tool invocation failed", exc_info=True)
            return [TextContent(type="text", text=str(e))]

    return server


def setup_handlers() -> None:
    """Set up signal handlers for graceful shutdown."""
    def handle_shutdown(signum, frame):
        log_with_data(logger, logging.DEBUG, "Shutting down runtime server...", {
            "signal": signum
        })
        # Cleanup all active environments
        for env_id in list(ENVIRONMENTS.keys()):
            try:
                log_with_data(logger, logging.DEBUG, "Cleaning up environment during shutdown", {
                    "env_id": env_id
                })
                asyncio.create_task(cleanup_environment(env_id))
            except Exception as e:
                logger.error(
                    "Error occurred",
                    extra={
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "traceback": traceback.format_exc(),
                        "env_id": env_id
                    }
                )
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)


async def serve() -> None:
    """Start the MCP runtime server."""
    configure_logging()
    
    log_with_data(logger, logging.DEBUG, "Starting runtime server", {
        "version": "0.1.0"
    })
    
    server = init_server()
    setup_handlers()
    
    async with stdio.stdio_server() as (read_stream, write_stream):
        logger.debug("Server streams initialized")
        options = server.create_initialization_options()
        await server.run(
            read_stream,
            write_stream,
            options
        )


def main() -> None:
    """Main entry point."""
    log_with_data(logger, logging.DEBUG, "Starting MCP runtime server main process")
    asyncio.run(serve())