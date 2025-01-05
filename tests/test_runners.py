"""Test runner detection and execution."""
import json
import pytest
import shutil
from pathlib import Path

from mcp_local_dev.environments.environment import create_environment, cleanup_environment
from mcp_local_dev.test_runners.runners import detect_runners, run_tests
from mcp_local_dev.test_runners.execution import auto_run_tests
from mcp_local_dev.types import RunConfig, RunnerType

@pytest.mark.asyncio
async def test_detect_runners(fixture_path: Path):
    """Test runner detection using fixture project."""
    project_dir = fixture_path / "python" / "pytest-project"
    env = await create_environment(project_dir)
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
    env = await create_environment(project_dir)
    try:
        config = RunConfig(
            runner=RunnerType.PYTEST,
            env=env,
            test_dirs=[env.sandbox.work_dir]
        )
        result = await run_tests(config)
        assert result["success"] is True
        assert result["summary"]["total"] > 0
        assert result["summary"]["passed"] > 0
    finally:
        cleanup_environment(env)

@pytest.mark.asyncio
async def test_auto_run_tests(fixture_path: Path):
    """Test auto-detecting and running tests using fixture project."""
    project_dir = fixture_path / "python" / "pytest-project"
    env = await create_environment(project_dir)
    try:
        results = await auto_run_tests(env)
        assert len(results) == 1
        assert results[0].type == "text"
        
        data = json.loads(results[0].text)
        assert data["success"] is True
        assert data["summary"]["total"] > 0
        assert data["summary"]["passed"] > 0
    finally:
        cleanup_environment(env)
