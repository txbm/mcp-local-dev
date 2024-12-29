"""MCP server implementation."""
import asyncio
import json
from typing import Any, Dict, List
import signal
import sys

from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.types as types
import mcp.server.stdio

from .types import (
    RuntimeManager,
    RuntimeConfig,
    TestConfig,
    CaptureConfig,
    CaptureMode,
    ResourceLimits
)
from .runtime import create_environment, cleanup_environment, run_in_env
from .testing import auto_detect_and_run_tests
from .sandbox import create_sandbox, cleanup_sandbox


class RuntimeServer:
    """MCP runtime server implementation."""

    def __init__(self) -> None:
        """Initialize the server."""
        self.server = Server("mcp-runtime-server")
        self._setup_handlers()
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        def handle_shutdown(signum, frame):
            print("\nShutting down runtime server...")
            # Cleanup all active environments
            for env_id in list(ACTIVE_ENVS.keys()):
                try:
                    asyncio.create_task(cleanup_environment(env_id, force=True))
                except Exception as e:
                    print(f"Error cleaning up environment {env_id}: {e}")
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)

    def _setup_handlers(self) -> None:
        """Set up MCP message handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List available runtime management tools."""
            return [
                types.Tool(
                    name="create_environment",
                    description="Create a new runtime environment with sandbox isolation",
                    parameters={
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
                    },
                    returns={
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "working_dir": {"type": "string"},
                            "created_at": {"type": "string", "format": "date-time"}
                        }
                    }
                ),
                types.Tool(
                    name="run_command",
                    description="Run a command in an isolated sandbox environment",
                    parameters={
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
                    },
                    returns={
                        "type": "object",
                        "properties": {
                            "stdout": {"type": "string"},
                            "stderr": {"type": "string"},
                            "exit_code": {"type": "integer"},
                            "start_time": {"type": "string", "format": "date-time"},
                            "end_time": {"type": "string", "format": "date-time"},
                            "stats": {
                                "type": "object",
                                "properties": {
                                    "peak_memory_mb": {"type": "number"},
                                    "avg_cpu_percent": {"type": "number"},
                                    "duration_seconds": {"type": "number"},
                                    "peak_cpu_percent": {"type": "number"}
                                }
                            }
                        }
                    }
                ),
                types.Tool(
                    name="auto_run_tests",
                    description="Auto-detect and run tests in a sandboxed environment",
                    parameters={
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
                    },
                    returns={
                        "type": "object",
                        "properties": {
                            "results": {
                                "type": "object",
                                "additionalProperties": {
                                    "type": "object",
                                    "properties": {
                                        "framework": {"type": "string"},
                                        "command": {"type": "string"},
                                        "passed": {"type": "integer"},
                                        "failed": {"type": "integer"},
                                        "total": {"type": "integer"},
                                        "execution_time": {"type": "number"},
                                        "coverage": {"type": ["number", "null"]},
                                        "failures": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        }
                                    }
                                }
                            },
                            "summary": {
                                "type": "object",
                                "properties": {
                                    "frameworks_detected": {"type": "integer"},
                                    "frameworks_run": {"type": "integer"},
                                    "all_passed": {"type": "boolean"},
                                    "total_tests": {"type": "integer"},
                                    "total_passed": {"type": "integer"},
                                    "total_failed": {"type": "integer"},
                                    "total_time": {"type": "number"}
                                }
                            }
                        }
                    }
                ),
                types.Tool(
                    name="cleanup_environment",
                    description="Clean up a sandboxed environment",
                    parameters={
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
                    },
                    returns={"type": "object"}
                )
            ]

        @self.server.tool_handler()
        async def handle_tool(name: str, arguments: Dict[str, Any]) -> Any:
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
                    return {
                        "id": env.id,
                        "working_dir": env.working_dir,
                        "created_at": env.created_at.isoformat()
                    }

                elif name == "run_command":
                    capture_config = CaptureConfig(
                        **arguments.get("capture_config", {})
                    )
                    process = await run_in_env(
                        arguments["env_id"],
                        arguments["command"],
                        capture_config
                    )
                    stdout, stderr = await process.communicate()
                    
                    return {
                        "stdout": stdout.decode() if stdout else "",
                        "stderr": stderr.decode() if stderr else "",
                        "exit_code": process.returncode,
                        "start_time": process.start_time.isoformat(),
                        "end_time": process.end_time.isoformat(),
                        "stats": process.stats if hasattr(process, "stats") else None
                    }

                elif name == "auto_run_tests":
                    results = await auto_detect_and_run_tests(
                        ACTIVE_ENVS[arguments["env_id"]],
                        include_coverage=arguments.get("include_coverage", True),
                        parallel=arguments.get("parallel", False)
                    )
                    return results

                elif name == "cleanup_environment":
                    await cleanup_environment(
                        arguments["env_id"],
                        force=arguments.get("force", False)
                    )
                    return {}

                raise ValueError(f"Unknown tool: {name}")
                
            except Exception as e:
                # Log error and re-raise with context
                print(f"Error executing {name}: {e}")
                raise

    async def serve(self) -> None:
        """Start the MCP server."""
        await mcp.server.stdio.serve(
            self.server,
            InitializationOptions(capabilities=["tools"])
        )


def main() -> None:
    """Main entry point."""
    server = RuntimeServer()
    try:
        asyncio.run(server.serve())
    except KeyboardInterrupt:
        print("\nServer stopped")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()