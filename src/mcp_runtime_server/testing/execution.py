"""Test execution module."""

import json
import shutil

import mcp.types as types
from mcp_runtime_server.environments.environment import Environment
from mcp_runtime_server.types import RunConfig, TestRunnerType, Runtime
from mcp_runtime_server.test_runners.results import format_test_results, parse_pytest_json
from mcp_runtime_server.sandboxes.sandbox import run_sandboxed_command
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)

def detect_test_runners(env: Environment) -> list[TestRunnerType]:
    """Detect available test runners for the environment"""
    logger.info({"event": "test_runner_detection_start", "project_dir": str(env.sandbox.work_dir)})
    
    # For now we only support pytest in Python environments
    if env.runtime_config.name == Runtime.PYTHON and shutil.which("pytest"):
        logger.info({"event": "test_runner_detected", "runner": TestRunnerType.PYTEST.value})
        return [TestRunnerType.PYTEST]
            
    logger.info({"event": "no_test_runners_detected"})
    return []

async def run_test_runner(config: RunConfig) -> Dict[str, Any]:
    """Run tests using the specified runner"""
    logger.info({
        "event": "test_runner_start", 
        "runner": config.runner.value,
        "working_dir": str(config.env.sandbox.work_dir)
    })

    if config.runner != TestRunnerType.PYTEST:
        error = f"Unsupported test runner: {config.runner}"
        logger.error({"event": "test_runner_error", "error": error})
        raise ValueError(error)

    cmd = f"python -m pytest -v --capture=no --tb=short -p no:warnings"
    process = await run_sandboxed_command(config.env.sandbox, cmd)
    stdout, stderr = await process.communicate()
    
    result = parse_pytest_json({
        "stdout": stdout.decode() if stdout else "",
        "stderr": stderr.decode() if stderr else "",
        "returncode": process.returncode
    })
    
    logger.info({
        "event": "test_runner_complete",
        "runner": config.runner.value,
        "success": result["success"]
    })

    return result


async def auto_run_tests(
    env: Environment,
) -> list[types.TextContent]:
    """Auto-detect and run tests in the environment."""
    runners = detect_test_runners(env)
    if not runners:
        logger.info(
            {"event": "no_test_runners_detected", "working_dir": str(env.sandbox.work_dir)}
        )
        return [
            types.TextContent(
                text=json.dumps(
                    {"success": False, "error": "No test runners detected"}
                ),
                type="text",
            )
        ]

    results = []
    for runner in runners:
        config = RunConfig(runner=runner, env=env, test_dirs=[env.sandbox.work_dir])
        result = await run_test_runner(config)
        results.append(result)

    all_passed = all(r.get("success", False) for r in results)
    logger.info(
        {
            "event": "test_run_complete",
            "all_passed": all_passed,
            "runner_count": len(runners),
        }
    )
    return format_test_results(runners[0].value, results[0] if results else {})
