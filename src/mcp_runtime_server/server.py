"""MCP server implementation."""
import asyncio
import json
from typing import Any, Dict, List

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
from .testing import run_tests


def create_mcp_server() -> Server:
    """Create and configure the MCP server instance."""
    server = Server("mcp-runtime-server")
    
    @server.list_tools()
    async def handle_list_tools() -> List[types.Tool]:
        """List available runtime management tools."""
        return [
            types.Tool(
                name="create_environment",
                description="Create a new runtime environment",
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
                description="Run a command in an environment",
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
                name="run_tests",
                description="Run tests in an environment",
                parameters={
                    "type": "object",
                    "properties": {
                        "env_id": {
                            "type": "string",
                            "description": "Environment identifier"
                        },
                        "tests": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "command": {"type": "string"},
                                    "expected_output": {"type": "string"},
                                    "expected_exit_code": {"type": "integer"},
                                    "timeout_seconds": {"type": "integer"},
                                    "env": {
                                        "type": "object",
                                        "additionalProperties": {"type": "string"}
                                    }
                                },
                                "required": ["name", "command"]
                            }
                        },
                        "parallel": {"type": "boolean"},
                        "max_concurrent": {"type": "integer"}
                    },
                    "required": ["env_id", "tests"]
                },
                returns={
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "result": {
                                "type": "string",
                                "enum": ["pass", "fail", "error", "timeout"]
                            },
                            "error_message": {"type": "string"},
                            "failure_details": {
                                "type": "object",
                                "additionalProperties": {"type": "string"}
                            },
                            "captured": {
                                "type": "object",
                                "properties": {
                                    "stdout": {"type": "string"},
                                    "stderr": {"type": "string"},
                                    "exit_code": {"type": "integer"}
                                }
                            }
                        }
                    }
                }
            ),
            types.Tool(
                name="cleanup_environment",
                description="Clean up a runtime environment",
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

    @server.invoke_tool()
    async def handle_invoke_tool(name: str, arguments: Dict[str, Any]) -> Any:
        """Handle tool invocations."""
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
            output = await run_in_env(
                arguments["env_id"],
                arguments["command"],
                capture_config
            )
            return {
                "stdout": output.stdout,
                "stderr": output.stderr,
                "exit_code": output.exit_code,
                "start_time": output.start_time.isoformat(),
                "end_time": output.end_time.isoformat(),
                "stats": {
                    "peak_memory_mb": output.stats.peak_memory_mb,
                    "avg_cpu_percent": output.stats.avg_cpu_percent,
                    "duration_seconds": output.stats.duration_seconds,
                    "peak_cpu_percent": output.stats.peak_cpu_percent
                } if output.stats else None
            }

        elif name == "run_tests":
            tests = [
                TestConfig(**test_config)
                for test_config in arguments["tests"]
            ]
            results = await run_tests(
                arguments["env_id"],
                tests,
                parallel=arguments.get("parallel", False),
                max_concurrent=arguments.get("max_concurrent")
            )
            return {
                name: {
                    "result": result.result.value,
                    "error_message": result.error_message,
                    "failure_details": result.failure_details,
                    "captured": {
                        "stdout": result.captured.stdout,
                        "stderr": result.captured.stderr,
                        "exit_code": result.captured.exit_code
                    }
                }
                for name, result in results.items()
            }

        elif name == "cleanup_environment":
            await cleanup_environment(
                arguments["env_id"],
                force=arguments.get("force", False)
            )
            return {}

        raise ValueError(f"Unknown tool: {name}")

    return server


async def serve() -> None:
    """Start the MCP server."""
    server = create_mcp_server()
    await mcp.server.stdio.serve(
        server,
        InitializationOptions(capabilities=["tools"])
    )


def main() -> None:
    """Main entry point."""
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        print("\nServer stopped")
    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()