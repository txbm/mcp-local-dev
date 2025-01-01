"""Tests for test execution functionality."""

import json
import pytest
from mcp.types import TextContent
from mcp_runtime_server.types import Environment
from mcp_runtime_server.environments.environment import create_environment
from mcp_runtime_server.testing.execution import auto_run_tests


@pytest.mark.asyncio
async def test_auto_run_tests_no_frameworks():
    """Test running tests with no frameworks detected."""
    env = await create_environment("https://github.com/username/no-tests-repo")
    result = await auto_run_tests(env)

    assert len(result) == 1
    assert isinstance(result[0], TextContent)

    data = json.loads(result[0].text)
    assert not data["success"]
    assert "No test frameworks detected" in data["error"]


@pytest.mark.asyncio
async def test_auto_run_tests_pytest():
    """Test running tests with pytest."""
    env = await create_environment("https://github.com/txbm/mcp-runtime-server")
    result = await auto_run_tests(env)

    assert len(result) == 1
    assert isinstance(result[0], TextContent)

    data = json.loads(result[0].text)
    assert data["success"]
    assert len(data["frameworks"]) == 1
    assert data["frameworks"][0]["framework"] == "pytest"

    framework = data["frameworks"][0]
    assert "total" in framework
    assert "passed" in framework
    assert "failed" in framework
    assert "skipped" in framework
    assert "test_cases" in framework


@pytest.mark.asyncio
async def test_auto_run_tests_multiple_frameworks():
    """Test running tests with multiple frameworks."""
    env = await create_environment("https://github.com/username/mixed-tests-repo")
    result = await auto_run_tests(env)

    assert len(result) == 1
    assert isinstance(result[0], TextContent)

    data = json.loads(result[0].text)
    assert data["success"]
    assert len(data["frameworks"]) == 2

    frameworks = {f["framework"] for f in data["frameworks"]}
    assert "pytest" in frameworks
    assert "unittest" in frameworks
