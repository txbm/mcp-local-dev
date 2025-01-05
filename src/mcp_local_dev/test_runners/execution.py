"""Test execution module."""

import json

import mcp.types as types
from mcp_local_dev.environments.environment import Environment
from mcp_local_dev.test_runners.runners import detect_test_runners, run_test_runner
from mcp_local_dev.types import RunConfig, TestRunnerType
from mcp_local_dev.test_runners.results import format_test_results
from mcp_local_dev.logging import get_logger

logger = get_logger(__name__)

async def auto_run_tests(env: Environment) -> list[types.TextContent]:
    """Auto-detect and run tests in environment."""
    try:
        runner = get_framework_runner(env)
        result = await runner(env)
        return format_test_results(result)
    except ValueError:
        return [types.TextContent(
            text=json.dumps({"success": False, "error": "No test runners detected"}),
            type="text"
        )]
