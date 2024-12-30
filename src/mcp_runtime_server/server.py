"""MCP server implementation."""
import asyncio
import json
import logging
import signal
import sys
from typing import Any, Dict, List

from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, CallToolResult, Result
from mcp.server import stdio

from mcp_runtime_server.errors import log_error
from mcp_runtime_server.runtime import create_environment, cleanup_environment, run_command
from mcp_runtime_server.types import RuntimeManager, RuntimeConfig
from mcp_runtime_server.logging import configure_logging, log_with_data

logger = logging.getLogger(__name__)

# Active environments
ENVIRONMENTS: Dict[str, Any] = {}


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
                            "enum": [m.value for m in RuntimeManager],
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
                name="run_command",
                description="Run a command in an isolated sandbox environment",
                inputSchema={
                    "type": "object", 
                    "properties": {
                        "env_id": {
                            "type": "string",
                            "description": "Environment identifier"
                        },
                        "command": {
                            "type": "string",
                            "description": "Command to run"
                        }
                    },
                    "required": ["env_id", "command"]
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
    async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle tool invocations."""
        try:
            log_with_data(logger, logging.DEBUG, f"Tool invocation started: {name}", {
                "tool": name,
                "arguments": arguments
            })

            if name == "create_environment":
                log_with_data(logger, logging.DEBUG, "Creating new environment", {
                    "manager": arguments["manager"],
                    "github_url": arguments["github_url"]
                })
                
                config = RuntimeConfig(
                    manager=RuntimeManager(arguments["manager"]),
                    github_url=arguments["github_url"]
                )
                env = await create_environment(config)
                result = {
                    "id": env.id,
                    "working_dir": env.working_dir,
                    "created_at": env.created_at.isoformat()
                }
                
                log_with_data(logger, logging.DEBUG, "Environment created successfully", result)
                
                # Properly construct the MCP response types
                text_content = TextContent(type="text", text=json.dumps(result))
                return CallToolResult(content=[text_content])

            elif name == "run_command":
                if "env_id" not in arguments:
                    logger.error("Missing env_id parameter")
                    raise ValueError("Missing env_id parameter")
                    
                if arguments["env_id"] not in ENVIRONMENTS:
                    logger.error(f"Unknown environment: {arguments['env_id']}")
                    raise ValueError(f"Unknown environment: {arguments['env_id']}")

                log_with_data(logger, logging.DEBUG, "Running command in environment", {
                    "env_id": arguments["env_id"],
                    "command": arguments["command"]
                })

                process = await run_command(
                    arguments["env_id"],
                    arguments["command"]
                )
                stdout, stderr = await process.communicate()
                
                result = {
                    "stdout": stdout.decode() if stdout else "",
                    "stderr": stderr.decode() if stderr else "",
                    "exit_code": process.returncode
                }
                
                log_with_data(logger, logging.DEBUG, "Command execution completed", {
                    "env_id": arguments["env_id"],
                    "exit_code": process.returncode
                })
                
                text_content = TextContent(type="text", text=json.dumps(result))
                return CallToolResult(content=[text_content])

            elif name == "run_tests":
                if "env_id" not in arguments:
                    logger.error("Missing env_id parameter")
                    raise ValueError("Missing env_id parameter")
                    
                if arguments["env_id"] not in ENVIRONMENTS:
                    logger.error(f"Unknown environment: {arguments['env_id']}")
                    raise ValueError(f"Unknown environment: {arguments['env_id']}")

                log_with_data(logger, logging.DEBUG, "Running tests in environment", {
                    "env_id": arguments["env_id"]
                })

                results = await auto_run_tests(ENVIRONMENTS[arguments["env_id"]])
                
                log_with_data(logger, logging.DEBUG, "Test execution completed", {
                    "env_id": arguments["env_id"],
                    "results": results
                })
                
                text_content = TextContent(type="text", text=json.dumps(results))
                return CallToolResult(content=[text_content])

            elif name == "cleanup":
                if "env_id" not in arguments:
                    logger.error("Missing env_id parameter")
                    raise ValueError("Missing env_id parameter")
                
                log_with_data(logger, logging.DEBUG, "Cleaning up environment", {
                    "env_id": arguments["env_id"]
                })
                    
                await cleanup_environment(arguments["env_id"])
                
                log_with_data(logger, logging.DEBUG, "Environment cleanup completed", {
                    "env_id": arguments["env_id"]
                })
                
                text_content = TextContent(type="text", text=json.dumps({"status": "success"}))
                return CallToolResult(content=[text_content])

            logger.error(f"Unknown tool requested: {name}")
            raise ValueError(f"Unknown tool: {name}")
            
        except Exception as e:
            log_error(e, {"tool": name, "arguments": arguments}, logger)
            logger.error("Tool invocation failed", exc_info=True, extra={
                "data": {
                    "tool": name,
                    "arguments": arguments,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            })
            # Properly construct error response
            text_content = TextContent(type="text", text=str(e))
            return CallToolResult(content=[text_content], isError=True)

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
                log_error(e, {"env_id": env_id}, logger)
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