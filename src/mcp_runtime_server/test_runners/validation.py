"""Test validation utilities."""

from typing import Dict, Any
from pathlib import Path

from mcp_runtime_server.types import Environment, ValidationResult



def check_test_environment(env: Environment) -> ValidationResult:
    """Check if an environment is properly configured for testing"""
    errors = []
    
    if not isinstance(env.sandbox.work_dir, Path):
        errors.append("sandbox work_dir must be a Path object")
    if not isinstance(env.sandbox.bin_dir, Path):
        errors.append("sandbox bin_dir must be a Path object") 
    if not env.sandbox.work_dir:
        errors.append("missing sandbox work directory")
    if not env.sandbox.bin_dir:
        errors.append("missing sandbox binary directory")
        
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors
    )


def check_test_results(results: Dict[str, Any]) -> ValidationResult:
    """Check test results format"""
    errors = []
    
    if not isinstance(results, dict):
        return ValidationResult(is_valid=False, errors=["results must be a dictionary"])

    required = ["success", "summary", "test_cases"]
    missing = [f for f in required if f not in results]
    if missing:
        errors.append(f"missing required fields: {', '.join(missing)}")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors
    )
"""Test validation utilities."""

from typing import Dict, Any
from pathlib import Path

from mcp_runtime_server.types import Environment, ValidationResult

def check_test_environment(env: Environment) -> ValidationResult:
    """Check if an environment is properly configured for testing"""
    errors = []
    
    if not isinstance(env.sandbox.work_dir, Path):
        errors.append("sandbox work_dir must be a Path object")
    if not isinstance(env.sandbox.bin_dir, Path):
        errors.append("sandbox bin_dir must be a Path object") 
    if not env.sandbox.work_dir:
        errors.append("missing sandbox work directory")
    if not env.sandbox.bin_dir:
        errors.append("missing sandbox binary directory")
        
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors
    )

def check_test_results(results: Dict[str, Any]) -> ValidationResult:
    """Check test results format."""
    if not isinstance(results, dict):
        return ValidationResult(is_valid=False, errors=["results must be a dictionary"])

    required = ["success", "summary", "test_cases"]
    missing = [f for f in required if f not in results]
    if missing:
        errors = [f"missing required fields: {', '.join(missing)}"]
        return ValidationResult(is_valid=False, errors=errors)

    return ValidationResult(is_valid=True, errors=[])
