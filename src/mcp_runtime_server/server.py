import asyncio
import json
import logging
import signal
import sys
from typing import Dict, Any, List
from mcp.server.lowlevel import Server
from mcp.types import Tool, TextContent, CallToolResult
from mcp.server import stdio

from mcp_runtime_server.environments import (create_environment, cleanup_environment, ENVIRONMENTS)
from mcp_runtime_server.testing.execution import auto_run_tests
from mcp_runtime_server.types import EnvironmentConfig
from mcp_runtime_server.logging import configure_logging, get_logger

logger = get_logger("server")

tools = [
    Tool(
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
    Tool(
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
    Tool(
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

async def init_server() -> Server:
    logger.info(f"Registered tools: {', '.join(t.name for t in tools)}")
    
    server = Server("mcp-runtime-server")

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        logger.debug("Tools requested")
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
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
                response = TextContent(text=json.dumps(result), type="text")
                return CallToolResult(content=[response])

            elif name == "run_tests":
                if arguments["env_id"] not in ENVIRONMENTS:
                    raise RuntimeError(f"Unknown environment: {arguments['env_id']}")

                env = ENVIRONMENTS[arguments["env_id"]]
                if not env.manager:
                    raise RuntimeError("Runtime not detected for environment")

                test_results = await auto_run_tests(env)
                if not isinstance(test_results, dict):
                    raise RuntimeError("Invalid test results")

                response = TextContent(text=json.dumps(test_results), type="text")
                return CallToolResult(content=[response])

            elif name == "cleanup":
                cleanup_environment(arguments["env_id"])
                response = TextContent(text=json.dumps({"status": "success"}), type="text")
                return CallToolResult(content=[response])

            raise RuntimeError(f"Unknown tool: {name}")

        except Exception as e:
            logger.exception(f"Tool invocation failed: {str(e)}")
            response = TextContent(text=str(e), type="text")
            return CallToolResult(content=[response], isError=True)

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
            options = server.create_initialization_options()
            await server.run(read_stream, write_stream, options)
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
