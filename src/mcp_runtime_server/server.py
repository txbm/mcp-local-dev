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
from mcp.types import INTERNAL_ERROR, INVALID_PARAMS

from mcp_runtime_server.errors import (
    RuntimeServerError,
    EnvironmentError,
    ResourceLimitError,
    BinaryNotFoundError,
    SandboxError,
    log_error
)
from mcp_runtime_server.runtime import create_environment, cleanup_environment, run_command
from mcp_runtime_server.testing import auto_run_tests
from mcp_runtime_server.types import (
    RuntimeManager,
    RuntimeConfig,
    CaptureConfig,
    CaptureMode, 
    ResourceLimits
)
from mcp_runtime_server.sandbox import create_sandbox, cleanup_sandbox
from mcp_runtime_server.logging import configure_logging, log_with_data

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
                        "package_name": {
                            "type": "string", 
                            "description": "Package to install"
                        },
                        "version": {
                            "type": "string",
                            "description": "Package version"
                        },
                        "args": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Additional arguments"
                        },
                        "env": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "description": "Environment variables"
                        },
                        "working_dir": {
                            "type": "string",
                            "description": "Working directory path"
                        },
                        "resource_limits": {
                            "type": "object",
                            "properties": {
                                "max_memory_mb": {"type": "integer"},
                                "max_cpu_percent": {"type": "number"},
                                "timeout_seconds": {"type": "integer"}
                            }
                        }
                    },
                    "required": ["manager", "package_name"]
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
                        },
                        "capture_config": {
                            "type": "object",
                            "properties": {
                                "mode": {
                                    "type": "string",
                                    "enum": [m.value for m in CaptureMode]
                                },
                                "max_output_size": {"type": "integer"},
                                "include_timestamps": {"type": "boolean"},
                                "include_stats": {"type": "boolean"}
                            }
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
                        },
                        "include_coverage": {
                            "type": "boolean",
                            "description": "Include coverage reporting"
                        },
                        "parallel": {
                            "type": "boolean",
                            "description": "Run tests in parallel"
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
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force cleanup of running processes"
                        }
                    },
                    "required": ["env_id"]
                }
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> types.ServerResult:
        """Handle tool invocations."""
        try:
            if name == "create_environment":
                config = RuntimeConfig(
                    manager=RuntimeManager(arguments["manager"]),
                    package_name=arguments["package_name"],
                    version=arguments.get("version"),
                    args=arguments.get("args", []),
                    env=arguments.get("env", {}),
                    working_dir=arguments.get("working_dir"),
                    resource_limits=ResourceLimits(**arguments["resource_limits"])
                    if "resource_limits" in arguments else None
                )
                env = await create_environment(config)
                content = types.TextContent(
                    type="text",
                    text=json.dumps({
                        "id": env.id,
                        "working_dir": env.working_dir,
                        "created_at": env.created_at.isoformat()
                    })
                )
                tool_result = types.CallToolResult(content=[content])
                return types.ServerResult(tool_result)

            elif name == "run_command":
                if "env_id" not in arguments:
                    raise EnvironmentError("Missing env_id parameter")
                    
                capture_config = CaptureConfig(
                    **arguments.get("capture_config", {})
                )
                process = await run_command(
                    arguments["env_id"],
                    arguments["command"],
                    capture_config
                )
                stdout, stderr = await process.communicate()
                
                content = types.TextContent(
                    type="text",
                    text=json.dumps({
                        "stdout": stdout.decode() if stdout else "",
                        "stderr": stderr.decode() if stderr else "",
                        "exit_code": process.returncode,
                        "start_time": process.start_time.isoformat(),
                        "end_time": process.end_time.isoformat(),
                        "stats": process.stats if hasattr(process, "stats") else None
                    })
                )
                tool_result = types.CallToolResult(content=[content])
                return types.ServerResult(tool_result)

            elif name == "run_tests":
                if "env_id" not in arguments:
                    raise EnvironmentError("Missing env_id parameter")
                    
                if arguments["env_id"] not in ENVIRONMENTS:
                    raise EnvironmentError(arguments["env_id"])
                    
                results = await auto_run_tests(
                    ENVIRONMENTS[arguments["env_id"]],
                    include_coverage=arguments.get("include_coverage", True),
                    parallel=arguments.get("parallel", False)
                )
                content = types.TextContent(
                    type="text", 
                    text=json.dumps(results)
                )
                tool_result = types.CallToolResult(content=[content])
                return types.ServerResult(tool_result)

            elif name == "cleanup":
                if "env_id" not in arguments:
                    raise EnvironmentError("Missing env_id parameter")
                    
                await cleanup_environment(
                    arguments["env_id"],
                    force=arguments.get("force", False)
                )
                content = types.TextContent(
                    type="text",
                    text=json.dumps({"status": "success"})
                )
                tool_result = types.CallToolResult(content=[content])
                return types.ServerResult(tool_result)

            raise RuntimeServerError(f"Unknown tool: {name}", INVALID_PARAMS)
            
        except Exception as e:
            if isinstance(e, RuntimeServerError):
                log_error(e, {"tool": name, "arguments": arguments}, logger)
                content = types.TextContent(
                    type="text",
                    text=str(e)
                )
                tool_result = types.CallToolResult(content=[content], isError=True)
                return types.ServerResult(tool_result)
            log_error(e, {"tool": name, "arguments": arguments}, logger)
            content = types.TextContent(
                type="text",
                text=str(e)
            )
            tool_result = types.CallToolResult(content=[content], isError=True)
            return types.ServerResult(tool_result)

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
                asyncio.create_task(cleanup_environment(env_id, force=True))
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