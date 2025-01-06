"""Test runner detection and execution."""

import pytest
from pathlib import Path

from mcp_local_dev.environments.environment import (
    create_environment_from_path,
    cleanup_environment,
)
from mcp_local_dev.test_runners.runners import (
    detect_runners,
    execute_runner,
    detect_and_run_tests,
)
from mcp_local_dev.types import RunConfig, RunnerType


@pytest.mark.asyncio
async def test_detect_runners(fixture_path: Path):
    """Test runner detection using fixture project."""
    project_dir = fixture_path / "python" / "pytest-project"
    env = await create_environment_from_path(project_dir)
    try:
        runners = await detect_runners(env)
        assert len(runners) == 1
        assert runners[0] == RunnerType.PYTEST
    finally:
        cleanup_environment(env)


@pytest.mark.asyncio
async def test_run_tests(fixture_path: Path):
    """Test running tests using fixture project."""
    project_dir = fixture_path / "python" / "pytest-project"
    env = await create_environment_from_path(project_dir)
    try:
        config = RunConfig(
            runner=RunnerType.PYTEST, env=env, test_dirs=[env.sandbox.work_dir]
        )
        result = await execute_runner(config)
        assert result["success"] is True
        assert result["summary"]["total"] > 0
        assert result["summary"]["passed"] > 0
    finally:
        cleanup_environment(env)


@pytest.mark.asyncio
async def test_auto_run_tests(fixture_path: Path):
    """Test auto-detecting and running tests using fixture project."""
    project_dir = fixture_path / "python" / "pytest-project"
    env = await create_environment_from_path(project_dir)
    try:
        results = await detect_and_run_tests(env)

        assert results["success"] is True
        assert results["summary"]["total"] > 0
        assert results["summary"]["passed"] > 0
    finally:
        cleanup_environment(env)
