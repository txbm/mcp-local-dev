"""Test validation utilities."""

from pathlib import Path
from typing import Dict, Any

from mcp_runtime_server.types import Environment, RunTestResult


def validate_test_environment(env: Environment) -> bool:
    """Validate that an environment is properly configured for testing."""
    if not isinstance(env.sandbox.work_dir, Path):
        raise ValueError("Invalid environment: sandbox work_dir must be a Path object")
    if not isinstance(env.sandbox.bin_dir, Path):
        raise ValueError("Invalid environment: sandbox bin_dir must be a Path object")
    if not env.sandbox.work_dir:
        raise ValueError("Invalid environment: missing sandbox work directory")
    if not env.sandbox.bin_dir:
        raise ValueError("Invalid environment: missing sandbox binary directory")
    return True


def validate_test_results(results: Dict[str, Any]) -> bool:
    """Validate test results match expected format."""
    if results is None:
        raise ValueError("Invalid test results: cannot be None")
    if not isinstance(results, dict):
        raise ValueError("Invalid test results: must be a dictionary")
    
    # Required fields
    if "framework" not in results:
        raise ValueError("Invalid test results: missing framework")
    if "success" not in results:
        raise ValueError("Invalid test results: missing success indicator")
    
    # Framework-specific validation
    framework = results["framework"]
    if framework == "pytest":
        _validate_pytest_results(results)
    elif framework == "unittest":
        _validate_unittest_results(results)
    else:
        raise ValueError(f"Invalid test results: unknown framework {framework}")
    
    return True


def _validate_pytest_results(results: Dict[str, Any]) -> None:
    """Validate pytest-specific results."""
    required_fields = ["total", "passed", "failed", "skipped", "test_cases"]
    missing = [f for f in required_fields if f not in results]
    if missing:
        raise ValueError(f"Invalid pytest results: missing fields {', '.join(missing)}")


def _validate_unittest_results(results: Dict[str, Any]) -> None:
    """Validate unittest-specific results."""
    required_fields = ["test_dirs", "results"]
    missing = [f for f in required_fields if f not in results]
    if missing:
        raise ValueError(f"Invalid unittest results: missing fields {', '.join(missing)}")
