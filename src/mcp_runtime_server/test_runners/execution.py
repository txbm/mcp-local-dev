"""Test execution module."""

import json

import mcp.types as types
from mcp_runtime_server.environments.environment import Environment
from mcp_runtime_server.test_runners.runners import detect_test_runners, run_test_runner
from mcp_runtime_server.types import RunConfig, TestRunnerType
from mcp_runtime_server.test_runners.results import format_test_results
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)

async def auto_run_tests(env: Environment) -> list[types.TextContent]:
    """Auto-detect and run tests in the environment"""
    runners = detect_test_runners(env)
    if not runners:
        logger.info({"event": "no_test_runners", "work_dir": str(env.sandbox.work_dir)})
        return [
            types.TextContent(
                text=json.dumps({"success": False, "error": "No test runners detected"}),
                type="text"
            )
        ]

    results = []
    for runner in runners:
        config = RunConfig(runner=runner, env=env, test_dirs=[env.sandbox.work_dir])
        result = await run_test_runner(config)
        results.append(result)

    all_passed = all(r.get("success", False) for r in results)
    logger.info({
        "event": "tests_complete",
        "all_passed": all_passed,
        "runner_count": len(runners)
    })
    
    return format_test_results(runners[0].value, results[0] if results else {})
