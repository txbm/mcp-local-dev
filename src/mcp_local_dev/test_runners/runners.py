"""Test runner utilities."""

from mcp_local_dev.logging import get_logger
from typing import Dict, Any, List, Callable, Awaitable, TypeAlias

from mcp_local_dev.types import Environment, RunnerType, RunConfig

RunnerTuple: TypeAlias = tuple[
    Callable[[Environment], Awaitable[bool]],
    Callable[[Environment], Awaitable[Dict[str, Any]]]
]
from mcp_local_dev.test_runners.pytest import check_pytest, run_pytest
from mcp_local_dev.test_runners.unittest import check_unittest, run_unittest
from mcp_local_dev.test_runners.jest import check_jest, run_jest
from mcp_local_dev.test_runners.vitest import check_vitest, run_vitest

logger = get_logger(__name__)

RUNNERS: Dict[RunnerType, RunnerTuple] = {
    RunnerType.PYTEST: (check_pytest, run_pytest),
    RunnerType.UNITTEST: (check_unittest, run_unittest),
    RunnerType.JEST: (check_jest, run_jest),
    RunnerType.VITEST: (check_vitest, run_vitest),
}


async def detect_runners(env: Environment) -> List[RunnerType]:
    """Detect available test runners for the environment"""
    logger.info(
        {"event": "runner_detection_start", "project_dir": str(env.sandbox.work_dir)}
    )

    detected = []
    for runner_type, (can_run, _) in RUNNERS.items():
        if await can_run(env):
            logger.info({"event": "runner_detected", "runner": runner_type.value})
            detected.append(runner_type)

    logger.info({"event": "no_runners_detected"})
    return detected


async def execute_runner(config: RunConfig) -> Dict[str, Any]:
    """Run tests using the specified runner"""
    logger.info(
        {
            "event": "test_run_start",
            "runner": config.runner.value,
            "working_dir": str(config.env.sandbox.work_dir),
        }
    )

    runner_funcs = RUNNERS.get(config.runner)
    if not runner_funcs:
        error = f"Unsupported test runner: {config.runner}"
        logger.error({"event": "test_run_error", "error": error})
        raise ValueError(error)

    _, run_tests = runner_funcs
    result = await run_tests(config.env)

    logger.info(
        {
            "event": "test_run_complete",
            "runner": config.runner.value,
            "success": result["success"],
            "summary": result.get("summary", {}),
            "coverage": {
                "lines": result["coverage"].lines if result.get("coverage") else 0,
                "statements": result["coverage"].statements if result.get("coverage") else 0,
                "branches": result["coverage"].branches if result.get("coverage") else 0,
                "functions": result["coverage"].functions if result.get("coverage") else 0,
            } if result.get("coverage") else None
        }
    )

    return result


async def detect_and_run_tests(env: Environment) -> Dict[str, Any]:
    """Auto-detect and run tests in environment."""

    runners = await detect_runners(env)
    if not runners:
        return {"success": False, "error": "No test runners detected"}

    config = RunConfig(runner=runners[0], env=env, test_dirs=[env.sandbox.work_dir])
    result = await execute_runner(config)

    return result
