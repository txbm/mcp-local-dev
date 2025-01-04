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
    """Auto-detect and run tests in the environment."""
    runners = detect_test_runners(env)
    if not runners:
        return [types.TextContent(
            text=json.dumps({"success": False, "error": "No test runners detected"}),
            type="text"
        )]

    config = RunConfig(
        runner=runners[0], 
        env=env,
        test_dirs=[env.sandbox.work_dir]
    )
    result = await run_test_runner(config)
    
    return format_test_results(runners[0].value, result)
