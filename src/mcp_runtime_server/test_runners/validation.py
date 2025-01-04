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
    """Check if test results match expected format"""
    errors = []
    
    if results is None:
        return ValidationResult(is_valid=False, errors=["results cannot be None"])
        
    if not isinstance(results, dict):
        return ValidationResult(is_valid=False, errors=["results must be a dictionary"])

    # Required fields
    if "framework" not in results:
        errors.append("missing framework field")
    if "success" not in results:
        errors.append("missing success indicator")

    # Framework-specific validation
    if "framework" in results:
        framework = results["framework"]
        if framework == "pytest":
            framework_result = _check_pytest_results(results)
        elif framework == "unittest":
            framework_result = _check_unittest_results(results)
        else:
            return ValidationResult(
                is_valid=False,
                errors=[f"unknown framework: {framework}"]
            )
            
        if not framework_result.is_valid:
            errors.extend(framework_result.errors)

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors
    )


def _check_pytest_results(results: Dict[str, Any]) -> ValidationResult:
    """Check pytest-specific results format"""
    required_fields = ["total", "passed", "failed", "skipped", "test_cases"]
    missing = [f for f in required_fields if f not in results]
    
    return ValidationResult(
        is_valid=len(missing) == 0,
        errors=[f"missing pytest fields: {', '.join(missing)}"] if missing else None
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
    """Check if test results match expected format"""
    errors = []
    
    if results is None:
        return ValidationResult(is_valid=False, errors=["results cannot be None"])
        
    if not isinstance(results, dict):
        return ValidationResult(is_valid=False, errors=["results must be a dictionary"])

    # Required fields
    if "success" not in results:
        errors.append("missing success indicator")
    if "summary" not in results:
        errors.append("missing test summary")
    if "tests" not in results:
        errors.append("missing test cases")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors
    )
