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


@pytest.mark.asyncio
async def test_detect_unittest_runner(fixture_path: Path):
    """Test unittest runner detection."""
    project_dir = fixture_path / "python" / "unittest-project"
    env = await create_environment_from_path(project_dir)
    try:
        runners = await detect_runners(env)
        assert len(runners) == 1
        assert runners[0] == RunnerType.UNITTEST
    finally:
        cleanup_environment(env)


@pytest.mark.asyncio
async def test_run_unittest(fixture_path: Path):
    """Test running unittest tests."""
    project_dir = fixture_path / "python" / "unittest-project"
    env = await create_environment_from_path(project_dir)
    try:
        config = RunConfig(
            runner=RunnerType.UNITTEST,
            env=env,
            test_dirs=[env.sandbox.work_dir]
        )
        result = await execute_runner(config)
        assert result["success"] is True
        assert result["summary"]["total"] > 0
        assert result["summary"]["passed"] > 0
    finally:
        cleanup_environment(env)


@pytest.mark.asyncio
async def test_detect_jest_runner(fixture_path: Path):
    """Test Jest runner detection."""
    project_dir = fixture_path / "javascript" / "jest-project"
    env = await create_environment_from_path(project_dir)
    try:
        runners = await detect_runners(env)
        assert len(runners) == 1
        assert runners[0] == RunnerType.JEST
    finally:
        cleanup_environment(env)


@pytest.mark.asyncio
async def test_run_jest(fixture_path: Path):
    """Test running Jest tests."""
    project_dir = fixture_path / "javascript" / "jest-project"
    env = await create_environment_from_path(project_dir)
    try:
        config = RunConfig(
            runner=RunnerType.JEST,
            env=env,
            test_dirs=[env.sandbox.work_dir]
        )
        result = await execute_runner(config)
        assert result["success"] is True
        assert result["summary"]["total"] > 0
        assert result["summary"]["passed"] > 0
    finally:
        cleanup_environment(env)


@pytest.mark.asyncio
async def test_detect_vitest_runner(fixture_path: Path):
    """Test Vitest runner detection."""
    project_dir = fixture_path / "javascript" / "vitest-project"
    env = await create_environment_from_path(project_dir)
    try:
        runners = await detect_runners(env)
        assert len(runners) == 1
        assert runners[0] == RunnerType.VITEST
    finally:
        cleanup_environment(env)


@pytest.mark.asyncio
async def test_pytest_coverage(fixture_path: Path):
    """Test that pytest coverage collection works."""
    project_dir = fixture_path / "python" / "pytest-project"
    env = await create_environment_from_path(project_dir)
    try:
        config = RunConfig(
            runner=RunnerType.PYTEST,
            env=env,
            test_dirs=[env.sandbox.work_dir]
        )
        result = await execute_runner(config)
        
        assert result["coverage"] is not None
        assert result["coverage"].lines > 0
        assert result["coverage"].statements > 0
        assert result["coverage"].branches > 0
        assert len(result["coverage"].files) > 0
        
        # Verify core.py is in coverage results
        core_file = next(f for f in result["coverage"].files.keys() if f.endswith("core.py"))
        assert result["coverage"].files[core_file] > 0
    finally:
        cleanup_environment(env)

@pytest.mark.asyncio
async def test_unittest_coverage(fixture_path: Path):
    """Test that unittest coverage collection works."""
    project_dir = fixture_path / "python" / "unittest-project"
    env = await create_environment_from_path(project_dir)
    try:
        config = RunConfig(
            runner=RunnerType.UNITTEST,
            env=env,
            test_dirs=[env.sandbox.work_dir]
        )
        result = await execute_runner(config)
        
        assert result["coverage"] is not None
        assert result["coverage"].lines > 0
        assert result["coverage"].statements > 0
        assert result["coverage"].branches > 0
        assert len(result["coverage"].files) > 0
        
        # Verify core.py is in coverage results
        core_file = next(f for f in result["coverage"].files.keys() if f.endswith("core.py"))
        assert result["coverage"].files[core_file] > 0
    finally:
        cleanup_environment(env)

@pytest.mark.asyncio
async def test_jest_coverage(fixture_path: Path):
    """Test that Jest coverage collection works."""
    project_dir = fixture_path / "javascript" / "jest-project"
    env = await create_environment_from_path(project_dir)
    try:
        config = RunConfig(
            runner=RunnerType.JEST,
            env=env,
            test_dirs=[env.sandbox.work_dir]
        )
        result = await execute_runner(config)
        
        assert result["coverage"] is not None
        assert result["coverage"].lines > 0
        assert result["coverage"].statements > 0
        assert result["coverage"].branches > 0
        assert result["coverage"].functions > 0
        assert len(result["coverage"].files) > 0
        
        # Verify core.js is in coverage results
        core_file = next(f for f in result["coverage"].files.keys() if f.endswith("core.js"))
        assert result["coverage"].files[core_file] > 0
    finally:
        cleanup_environment(env)

@pytest.mark.asyncio
async def test_vitest_coverage(fixture_path: Path):
    """Test that Vitest coverage collection works."""
    project_dir = fixture_path / "javascript" / "vitest-project"
    env = await create_environment_from_path(project_dir)
    try:
        config = RunConfig(
            runner=RunnerType.VITEST,
            env=env,
            test_dirs=[env.sandbox.work_dir]
        )
        result = await execute_runner(config)
        assert result["success"] is True
        assert result["summary"]["total"] > 0
        assert result["summary"]["passed"] > 0
    finally:
        cleanup_environment(env)


@pytest.mark.asyncio
async def test_runner_detection_precedence(fixture_path: Path):
    """Test that only one runner is detected per project."""
    # Test Python projects
    pytest_dir = fixture_path / "python" / "pytest-project"
    unittest_dir = fixture_path / "python" / "unittest-project"
    
    env = await create_environment_from_path(pytest_dir)
    try:
        runners = await detect_runners(env)
        assert len(runners) == 1
        assert runners[0] == RunnerType.PYTEST
    finally:
        cleanup_environment(env)

    env = await create_environment_from_path(unittest_dir)
    try:
        runners = await detect_runners(env)
        assert len(runners) == 1
        assert runners[0] == RunnerType.UNITTEST
    finally:
        cleanup_environment(env)

    # Test JavaScript projects
    jest_dir = fixture_path / "javascript" / "jest-project"
    vitest_dir = fixture_path / "javascript" / "vitest-project"
    
    env = await create_environment_from_path(jest_dir)
    try:
        runners = await detect_runners(env)
        assert len(runners) == 1
        assert runners[0] == RunnerType.JEST
    finally:
        cleanup_environment(env)

    env = await create_environment_from_path(vitest_dir)
    try:
        runners = await detect_runners(env)
        assert len(runners) == 1
        assert runners[0] == RunnerType.VITEST
    finally:
        cleanup_environment(env)
