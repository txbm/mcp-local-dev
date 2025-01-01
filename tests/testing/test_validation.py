"""Tests for test validation functionality."""

import pytest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from mcp_runtime_server.types import Environment, RunTestResult, Runtime, Sandbox
from mcp_runtime_server.testing.validation import (
    validate_test_environment,
    validate_test_results,
    _validate_pytest_results,
    _validate_unittest_results
)


def test_validate_test_environment():
    """Test validation of test environment."""
    tempdir = TemporaryDirectory()

    # Test valid environment
    sandbox = Sandbox(
        root=Path("/path/to/root"),
        work_dir=Path("/path/to/work"),
        bin_dir=Path("/path/to/bin"),
        env_vars={}
    )
    
    env = Environment(
        id="test-env",
        runtime=Runtime.PYTHON,
        created_at=datetime.now(),
        env_vars={},
        sandbox=sandbox,
        tempdir=tempdir
    )
    assert validate_test_environment(env) is True
    
    # Test invalid environment - string instead of Path in sandbox
    sandbox_invalid_type = Sandbox(
        root=Path("/path/to/root"),
        work_dir="/path/to/work",  # string instead of Path
        bin_dir=Path("/path/to/bin"),
        env_vars={}
    )
    
    env = Environment(
        id="test-env",
        runtime=Runtime.PYTHON,
        created_at=datetime.now(),
        env_vars={},
        sandbox=sandbox_invalid_type,
        tempdir=tempdir
    )
    
    with pytest.raises(ValueError, match="sandbox work_dir must be a Path object"):
        validate_test_environment(env)
    
    # Test invalid environment - empty work_dir in sandbox
    sandbox_empty_path = Sandbox(
        root=Path("/path/to/root"),
        work_dir=Path(""),  # empty path
        bin_dir=Path("/path/to/bin"),
        env_vars={}
    )
    
    env = Environment(
        id="test-env",
        runtime=Runtime.PYTHON,
        created_at=datetime.now(),
        env_vars={},
        sandbox=sandbox_empty_path,
        tempdir=tempdir
    )
    
    with pytest.raises(ValueError, match="missing sandbox work directory"):
        validate_test_environment(env)
    
    # Test invalid environment - empty bin_dir in sandbox
    sandbox_empty_bin = Sandbox(
        root=Path("/path/to/root"),
        work_dir=Path("/path/to/work"),
        bin_dir=Path(""),  # empty path
        env_vars={}
    )
    
    env = Environment(
        id="test-env",
        runtime=Runtime.PYTHON,
        created_at=datetime.now(),
        env_vars={},
        sandbox=sandbox_empty_bin,
        tempdir=tempdir
    )
    
    with pytest.raises(ValueError, match="missing sandbox binary directory"):
        validate_test_environment(env)
    
    tempdir.cleanup()


def test_validate_test_results_basic():
    """Test basic validation of test results."""
    # Test None results
    with pytest.raises(ValueError, match="cannot be None"):
        validate_test_results(None)
    
    # Test non-dict results
    with pytest.raises(ValueError, match="must be a dictionary"):
        validate_test_results(["not", "a", "dict"])
    
    # Test missing framework
    with pytest.raises(ValueError, match="missing framework"):
        validate_test_results({"success": True})
    
    # Test missing success
    with pytest.raises(ValueError, match="missing success indicator"):
        validate_test_results({"framework": "pytest"})
    
    # Test unknown framework
    with pytest.raises(ValueError, match="unknown framework"):
        validate_test_results({"framework": "unknown", "success": True})


def test_validate_pytest_results():
    """Test validation of pytest results."""
    # Valid pytest results
    valid_results = {
        "framework": "pytest",
        "success": True,
        "total": 5,
        "passed": 4,
        "failed": 1,
        "skipped": 0,
        "test_cases": []
    }
    assert validate_test_results(valid_results) is True
    
    # Test missing required fields
    invalid_results = {
        "framework": "pytest",
        "success": True,
        "total": 5,
        # missing other required fields
    }
    with pytest.raises(ValueError, match="missing fields"):
        validate_test_results(invalid_results)


def test_validate_unittest_results():
    """Test validation of unittest results."""
    # Valid unittest results
    valid_results = {
        "framework": "unittest",
        "success": True,
        "test_dirs": ["/path/to/tests"],
        "results": [
            {
                "success": True,
                "test_dir": "/path/to/tests",
                "stdout": "OK",
                "stderr": ""
            }
        ]
    }
    assert validate_test_results(valid_results) is True
    
    # Test missing required fields
    invalid_results = {
        "framework": "unittest",
        "success": True,
        # missing test_dirs and results
    }
    with pytest.raises(ValueError, match="missing fields"):
        validate_test_results(invalid_results)