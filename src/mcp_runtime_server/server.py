"""MCP server implementation."""
import asyncio
import json
import logging
import signal
import sys
from typing import Any, Dict, List

from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import stdio

from mcp_runtime_server.errors import log_error
from mcp_runtime_server.runtime import create_environment, cleanup_environment, run_command
from mcp_runtime_server.types import RuntimeManager, RuntimeConfig
from mcp_runtime_server.logging import configure_logging

logger = logging.getLogger(__name__)

# Active environments
ENVIRONMENTS: Dict[str, Any] = {}


def init_server() -> Server:
    """Initialize the MCP runtime server."""
    server = Server("mcp-runtime-server")

    @server.list_tools() 
    async def list_tools() -> List[types.Tool]:
        """List available runtime management tools."""
        return [
            types.Tool(
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
            types.Tool(
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
            types.Tool(
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
            types.Tool(
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

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> types.CallToolResult:
        """Handle tool invocations."""
        try:
            if name == "create_environment":
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
                return types.CallToolResult(content=[types.TextContent(
                    type="text",
                    text=json.dumps(result)
                )])

            elif name == "run_command":
                if "env_id" not in arguments:
                    raise ValueError("Missing env_id parameter")
                    
                if arguments["env_id"] not in ENVIRONMENTS:
                    raise ValueError(f"Unknown environment: {arguments['env_id']}")

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
                return types.CallToolResult(content=[types.TextContent(
                    type="text",
                    text=json.dumps(result)
                )])

            elif name == "run_tests":
                if "env_id" not in arguments:
                    raise ValueError("Missing env_id parameter")
                    
                if arguments["env_id"] not in ENVIRONMENTS:
                    raise ValueError(f"Unknown environment: {arguments['env_id']}")

                results = await auto_run_tests(ENVIRONMENTS[arguments["env_id"]])
                return types.CallToolResult(content=[types.TextContent(
                    type="text", 
                    text=json.dumps(results)
                )])

            elif name == "cleanup":
                if "env_id" not in arguments:
                    raise ValueError("Missing env_id parameter")
                    
                await cleanup_environment(arguments["env_id"])
                return types.CallToolResult(content=[types.TextContent(
                    type="text",
                    text=json.dumps({"status": "success"})
                )])

            raise ValueError(f"Unknown tool: {name}")
            
        except Exception as e:
            log_error(e, {"tool": name, "arguments": arguments}, logger)
            return types.CallToolResult(content=[types.TextContent(
                type="text",
                text=str(e)
            )], isError=True)

    return server


def setup_handlers() -> None:
    """Set up signal handlers for graceful shutdown."""
    def handle_shutdown(signum, frame):
        logger.debug("Shutting down runtime server...", extra={
            "data": {"signal": signum}
        })
        # Cleanup all active environments
        for env_id in list(ENVIRONMENTS.keys()):
            try:
                asyncio.create_task(cleanup_environment(env_id))
            except Exception as e:
                log_error(e, {"env_id": env_id}, logger)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)


async def serve() -> None:
    """Start the MCP runtime server."""
    configure_logging()
    
    logger.debug("Starting runtime server", extra={
        "data": {"version": "0.1.0"}
    })
    
    server = init_server()
    setup_handlers()
    
    async with stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-runtime-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )


def main() -> None:
    """Main entry point."""
    asyncio.run(serve())