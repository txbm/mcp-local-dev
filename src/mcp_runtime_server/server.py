"""MCP server implementation."""
import asyncio
import json
import logging
from typing import Any, Dict, List
import signal
import sys

from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import stdio
from mcp.types import INTERNAL_ERROR, INVALID_PARAMS

from mcp_runtime_server.types import (
    RuntimeManager,
    RuntimeConfig,
    TestConfig,
    CaptureConfig,
    CaptureMode,
    ResourceLimits
)
from mcp_runtime_server.runtime import create_environment, cleanup_environment, run_in_env
from mcp_runtime_server.testing import auto_detect_and_run_tests
from mcp_runtime_server.sandbox import create_sandbox, cleanup_sandbox
from mcp_runtime_server.errors import (
    RuntimeServerError,
    InvalidEnvironmentError,
    ResourceLimitError,
    BinaryNotFoundError,
    SandboxError
)
from mcp_runtime_server.logging import setup_logging


logger = logging.getLogger(__name__)
ACTIVE_ENVS: Dict[str, Any] = {}


def init_runtime_server() -> Server:
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
                name="auto_run_tests",
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
                name="cleanup_environment",
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
    async def call_tool(name: str, arguments: Dict[str, Any]) -> types.CallToolResult:
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
                return types.CallToolResult(
                    content=[types.TextContent(
                        type="text",
                        text=json.dumps({
                            "id": env.id,
                            "working_dir": env.working_dir,
                            "created_at": env.created_at.isoformat()
                        })
                    )]
                )

            elif name == "run_command":
                if "env_id" not in arguments:
                    raise InvalidEnvironmentError("Missing env_id parameter")
                    
                capture_config = CaptureConfig(
                    **arguments.get("capture_config", {})
                )
                process = await run_in_env(
                    arguments["env_id"],
                    arguments["command"],
                    capture_config
                )
                stdout, stderr = await process.communicate()
                
                return types.CallToolResult(
                    content=[types.TextContent(
                        type="text",
                        text=json.dumps({
                            "stdout": stdout.decode() if stdout else "",
                            "stderr": stderr.decode() if stderr else "",
                            "exit_code": process.returncode,
                            "start_time": process.start_time.isoformat(),
                            "end_time": process.end_time.isoformat(),
                            "stats": process.stats if hasattr(process, "stats") else None
                        })
                    )]
                )

            elif name == "auto_run_tests":
                if "env_id" not in arguments:
                    raise InvalidEnvironmentError("Missing env_id parameter")
                    
                if arguments["env_id"] not in ACTIVE_ENVS:
                    raise InvalidEnvironmentError(arguments["env_id"])
                    
                results = await auto_detect_and_run_tests(
                    ACTIVE_ENVS[arguments["env_id"]],
                    include_coverage=arguments.get("include_coverage", True),
                    parallel=arguments.get("parallel", False)
                )
                return types.CallToolResult(
                    content=[types.TextContent(
                        type="text",
                        text=json.dumps(results)
                    )]
                )

            elif name == "cleanup_environment":
                if "env_id" not in arguments:
                    raise InvalidEnvironmentError("Missing env_id parameter")
                    
                await cleanup_environment(
                    arguments["env_id"],
                    force=arguments.get("force", False)
                )
                return types.CallToolResult(
                    content=[types.TextContent(
                        type="text",
                        text=json.dumps({"status": "success"})
                    )]
                )

            raise RuntimeServerError(f"Unknown tool: {name}", INVALID_PARAMS)
            
        except (RuntimeServerError, BaseException) as e:
            if isinstance(e, RuntimeServerError):
                logger.error(f"Tool execution error: {str(e)}", exc_info=True)
                raise types.ErrorData(
                    code=e.code,
                    message=str(e),
                    data=e.details if hasattr(e, 'details') else None
                )
            else:
                logger.error(f"Unexpected error in tool execution: {str(e)}", exc_info=True)
                raise RuntimeServerError(str(e), INTERNAL_ERROR)


    return server


def setup_signal_handlers() -> None:
    """Set up signal handlers for graceful shutdown."""
    def handle_shutdown(signum, frame):
        logger.info("\nShutting down runtime server...")
        # Cleanup all active environments
        for env_id in list(ACTIVE_ENVS.keys()):
            try:
                asyncio.create_task(cleanup_environment(env_id, force=True))
            except BaseException as e:
                logger.error(f"Error cleaning up environment {env_id}: {e}")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)


async def serve_runtime() -> None:
    """Start the MCP runtime server."""
    setup_logging()  # Configure logging with filters
    server = init_runtime_server()
    setup_signal_handlers()
    
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
    try:
        asyncio.run(serve_runtime())
    except KeyboardInterrupt:
        logger.info("\nServer stopped")
    except BaseException as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()