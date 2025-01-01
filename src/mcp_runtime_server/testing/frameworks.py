"""Test framework utilities."""

import json
import os
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Set

from mcp_runtime_server.environments.commands import run_command
from mcp_runtime_server.types import Environment
from mcp_runtime_server.testing.results import parse_pytest_json
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


class TestFramework(str, Enum):
    PYTEST = "pytest"
    UNITTEST = "unittest"  # Added support for unittest


def _has_test_files(directory: Path, pattern: str) -> bool:
    """Check if directory contains files matching the test pattern."""
    if not directory.exists():
        return False

    for root, _, files in os.walk(directory):
        if any(f for f in files if f.startswith("test_") and f.endswith(pattern)):
            return True
    return False


def _check_file_imports(file_path: Path, import_names: List[str]) -> bool:
    """Check if a Python file imports any of the specified modules."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            return any(
                f"import {name}" in content or f"from {name}" in content
                for name in import_names
            )
    except Exception:
        return False


def _find_test_dirs(project_dir: Path) -> Set[Path]:
    """Find all potential test directories in the project."""
    test_dirs = set()

    # Common test directory names
    test_dir_names = ["tests", "test", "testing", "unit_tests", "integration_tests"]

    # Search for test directories
    for root, dirs, _ in os.walk(project_dir):
        root_path = Path(root)

        # Add directories that match common test directory names
        test_dirs.update(root_path / d for d in dirs if d.lower() in test_dir_names)

        # Add directories containing test files
        test_dirs.update(
            root_path / d for d in dirs if _has_test_files(root_path / d, ".py")
        )

    return test_dirs


def detect_frameworks(project_dir: str) -> List[TestFramework]:
    """Detect test frameworks in a project directory.

    Detection methods:
    1. Check for framework-specific configuration files
    2. Scan for test files and analyze imports
    3. Check project configuration files
    4. Look for framework-specific patterns in test files
    """
    path = Path(project_dir)
    frameworks = set()

    # Find all potential test directories
    test_dirs = _find_test_dirs(path)

    if not test_dirs:
        logger.warning({"event": "no_test_directories_found", "project_dir": str(path)})
        return list(frameworks)

    for test_dir in test_dirs:
        logger.info({"event": "test_directory_found", "path": str(test_dir)})

        # Check for pytest indicators
        pytest_indicators = [
            test_dir / "conftest.py",  # Conftest file
            path / "pytest.ini",  # Pytest config
            path / "setup.cfg",  # Setup.cfg might contain pytest config
            path / "tox.ini",  # Tox config might contain pytest config
        ]

        if any(p.exists() for p in pytest_indicators):
            frameworks.add(TestFramework.PYTEST)
            logger.info(
                {
                    "event": "pytest_config_found",
                    "indicators": [str(p) for p in pytest_indicators if p.exists()],
                }
            )

        # Scan Python files in test directory for framework imports
        for root, _, files in os.walk(test_dir):
            for file in files:
                if not file.endswith(".py"):
                    continue

                file_path = Path(root) / file

                # Check pytest imports
                if _check_file_imports(file_path, ["pytest"]):
                    frameworks.add(TestFramework.PYTEST)
                    logger.info(
                        {"event": "pytest_import_found", "file": str(file_path)}
                    )

                # Check unittest imports
                if _check_file_imports(file_path, ["unittest"]):
                    frameworks.add(TestFramework.UNITTEST)
                    logger.info(
                        {"event": "unittest_import_found", "file": str(file_path)}
                    )

    # Check pyproject.toml for test dependencies
    pyproject_path = path / "pyproject.toml"
    if pyproject_path.exists():
        try:
            with open(pyproject_path, "r", encoding="utf-8") as f:
                content = f.read()
                if "pytest" in content:
                    frameworks.add(TestFramework.PYTEST)
                    logger.info(
                        {
                            "event": "pytest_dependency_found",
                            "file": str(pyproject_path),
                        }
                    )
        except Exception as e:
            logger.warning({"event": "pyproject_toml_read_error", "error": str(e)})

    if not frameworks:
        # If no specific framework is detected but test files exist,
        # default to unittest if there are test case classes
        for test_dir in test_dirs:
            for root, _, files in os.walk(test_dir):
                for file in files:
                    if not file.startswith("test_") or not file.endswith(".py"):
                        continue

                    file_path = Path(root) / file
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            if "class Test" in content and "TestCase" in content:
                                frameworks.add(TestFramework.UNITTEST)
                                logger.info(
                                    {
                                        "event": "unittest_pattern_found",
                                        "file": str(file_path),
                                    }
                                )
                    except Exception:
                        continue

    # Log detection summary
    logger.info(
        {
            "event": "framework_detection_complete",
            "detected_frameworks": [f.value for f in frameworks],
            "test_directories": [str(d) for d in test_dirs],
        }
    )

    return list(frameworks)


async def run_pytest(env: Environment) -> Dict[str, Any]:
    """Run pytest in the environment."""
    result = {"framework": TestFramework.PYTEST.value}

    try:
        pytest_path = env.bin_dir / "pytest"
        if not pytest_path.exists():
            pytest_path = env.bin_dir / "pytest.exe"

        if not pytest_path.exists():
            raise RuntimeError("pytest not found in environment")

        # Search for test directories
        test_dirs = _find_test_dirs(env.work_dir)
        if not test_dirs:
            raise RuntimeError("No test directories found")

        # Run pytest for each test directory
        all_results = []
        for test_dir in test_dirs:
            process = await run_command(
                f"{pytest_path} -vv --no-header --json-report --json-report-file=- {test_dir} 2>/dev/stderr",
                str(env.work_dir),
                env.env_vars,
            )
            stdout, stderr = await process.communicate()

            try:
                report = json.loads(stderr)
                summary = parse_pytest_json(report)
                all_results.append(summary)
            except json.JSONDecodeError:
                all_results.append(
                    {
                        "success": process.returncode == 0,
                        "error": f"Failed to parse test output for {test_dir}",
                        "stdout": stdout.decode() if stdout else "",
                        "stderr": stderr.decode() if stderr else "",
                    }
                )

        # Combine results
        if all_results:
            result.update(
                {
                    "success": all(r.get("success", False) for r in all_results),
                    "test_dirs": [str(d) for d in test_dirs],
                    "results": all_results,
                }
            )
        else:
            result.update({"success": False, "error": "No test results generated"})

    except Exception as e:
        result.update({"success": False, "error": str(e)})

    return result


async def run_unittest(env: Environment) -> Dict[str, Any]:
    """Run unittest in the environment."""
    result = {"framework": TestFramework.UNITTEST.value}

    try:
        python_path = env.bin_dir / "python"
        if not python_path.exists():
            python_path = env.bin_dir / "python.exe"

        if not python_path.exists():
            raise RuntimeError("python not found in environment")

        # Search for test directories
        test_dirs = _find_test_dirs(env.work_dir)
        if not test_dirs:
            raise RuntimeError("No test directories found")

        # Run unittest discovery for each test directory
        all_results = []
        for test_dir in test_dirs:
            process = await run_command(
                f"{python_path} -m unittest discover -v {test_dir}",
                str(env.work_dir),
                env.env_vars,
            )
            stdout, stderr = await process.communicate()

            all_results.append(
                {
                    "success": process.returncode == 0,
                    "test_dir": str(test_dir),
                    "stdout": stdout.decode() if stdout else "",
                    "stderr": stderr.decode() if stderr else "",
                }
            )

        # Combine results
        result.update(
            {
                "success": all(r.get("success", False) for r in all_results),
                "test_dirs": [str(d) for d in test_dirs],
                "results": all_results,
            }
        )

    except Exception as e:
        result.update({"success": False, "error": str(e)})

    return result


async def run_framework_tests(
    framework: TestFramework, env: Environment
) -> Dict[str, Any]:
    """Run tests for a specific framework in the environment."""
    logger.info(
        {
            "event": "framework_test_start",
            "framework": framework.value,
            "working_dir": str(env.work_dir),
        }
    )

    if framework == TestFramework.PYTEST:
        result = await run_pytest(env)
    elif framework == TestFramework.UNITTEST:
        result = await run_unittest(env)
    else:
        error = f"Unsupported framework: {framework}"
        logger.error({"event": "framework_test_error", "error": error})
        raise ValueError(error)

    logger.info(
        {
            "event": "framework_test_complete",
            "framework": framework.value,
            "success": result.get("success", False),
        }
    )

    return result
