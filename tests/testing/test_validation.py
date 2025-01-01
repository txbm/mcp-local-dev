"""Tests for test validation functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from mcp_runtime_server.types import Environment
from mcp_runtime_server.testing.validation import (
    validate_test_environment,
    validate_test_results
)


def test_validate_test_environment():
    """Test validation of test environment."""
    # Test valid environment
    env = Mock(spec=Environment)
    env.work_dir = Path("/path/to/work")
    env.bin_dir = Path("/path/to/bin")
    
    assert validate_test_environment(env) is True
    
    # Test invalid environment - missing work_dir
    env = Mock(spec=Environment)
    env.work_dir = None
    env.bin_dir = Path("/path/to/bin")
    
    with pytest.raises(ValueError, match="Invalid environment: missing work directory"):
        validate_test_environment(env)
    
    # Test invalid environment - missing bin_dir
    env = Mock(spec=Environment)
    env.work_dir = Path("/path/to/work")
    env.bin_dir = None
    
    with pytest.raises(ValueError, match="Invalid environment: missing binary directory"):
        validate_test_environment(env)
    
    # Test invalid environment - non-Path objects
    env = Mock(spec=Environment)
    env.work_dir = "/path/to/work"  # string instead of Path
    env.bin_dir = Path("/path/to/bin")
    
    with pytest.raises(ValueError, match="Invalid environment: work_dir must be a Path object"):
        validate_test_environment(env)


def test_validate_test_results():
    """Test validation of test results."""
    # Test valid pytest results
    pytest_results = {
        "framework": "pytest",
        "success": True,
        "total": 10,
        "passed": 8,
        "failed": 1,
        "skipped": 1,
        "test_cases": [
            {
                "name": "test_something",
                "file": "test_file.py",
                "outcome": "passed",
                "duration": 0.1
            }
        ]
    }
    
    assert validate_test_results(pytest_results) is True
    
    # Test valid unittest results
    unittest_results = {
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
    
    assert validate_test_results(unittest_results) is True
    
    # Test invalid results - missing framework
    invalid_results = {
        "success": True,
        "total": 10,
        "passed": 10
    }
    
    with pytest.raises(ValueError, match="Invalid test results: missing framework"):
        validate_test_results(invalid_results)
    
    # Test invalid results - missing success flag
    invalid_results = {
        "framework": "pytest",
        "total": 10,
        "passed": 10
    }
    
    with pytest.raises(ValueError, match="Invalid test results: missing success indicator"):
        validate_test_results(invalid_results)
    
    # Test invalid results - invalid framework
    invalid_results = {
        "framework": "unknown",
        "success": True,
        "total": 10
    }
    
    with pytest.raises(ValueError, match="Invalid test results: unknown framework"):
        validate_test_results(invalid_results)
    
    # Test invalid pytest results - missing required fields
    invalid_pytest = {
        "framework": "pytest",
        "success": True,
        # missing total, passed, failed, skipped
    }
    
    with pytest.raises(ValueError, match="Invalid pytest results: missing required fields"):
        validate_test_results(invalid_pytest)
    
    # Test invalid unittest results - missing required fields
    invalid_unittest = {
        "framework": "unittest",
        "success": True,
        # missing test_dirs, results
    }
    
    with pytest.raises(ValueError, match="Invalid unittest results: missing required fields"):
        validate_test_results(invalid_unittest)
    
    # Test invalid results type
    with pytest.raises(ValueError, match="Invalid test results: must be a dictionary"):
        validate_test_results(["not", "a", "dict"])
    
    # Test None results
    with pytest.raises(ValueError, match="Invalid test results: cannot be None"):
        validate_test_results(None)