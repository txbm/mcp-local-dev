"""Test framework utilities."""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Set

from mcp_runtime_server.sandboxes.sandbox import run_sandboxed_command
from mcp_runtime_server.types import Environment, FrameworkType, RunConfig, Runtime
from mcp_runtime_server.logging import get_logger
from mcp_runtime_server.testing.results import parse_pytest_json

logger = get_logger(__name__)



def _has_test_files(directory: Path, env: Environment) -> bool:
    """Check if directory contains files matching the test pattern."""
    if not directory.exists():
        logger.debug(
            {
                "event": "checking_test_directory",
                "directory": str(directory),
                "exists": False,
            }
        )
        return False

    pattern = ".py" if env.runtime_config.name == Runtime.PYTHON else ".test.js"
    for root, _, files in os.walk(directory):
        test_files = [f for f in files if f.startswith("test_") and f.endswith(pattern)]
        logger.debug(
            {
                "event": "scanning_directory",
                "directory": root,
                "test_files_found": test_files,
            }
        )
        if test_files:
            return True
    return False


def _check_file_imports(file_path: Path, import_names: List[str]) -> bool:
    """Check if a Python file imports any of the specified modules."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            chunk_size = 8192
            while chunk := f.read(chunk_size):
                found_imports = [
                    name
                    for name in import_names
                    if f"import {name}" in chunk or f"from {name}" in chunk
                ]
                if found_imports:
                    logger.debug(
                        {
                            "event": "imports_found",
                            "file": str(file_path),
                            "found": found_imports,
                        }
                    )
                    return True
        logger.debug(
            {
                "event": "no_imports_found",
                "file": str(file_path),
                "searched_for": import_names,
            }
        )
        return False
    except Exception as e:
        logger.error(
            {
                "event": "file_import_check_error",
                "file": str(file_path),
                "error": str(e),
            }
        )
        return False


def _find_test_dirs(project_dir: Path, env: Environment) -> Set[Path]:
    """Find all potential test directories in the project."""
    test_dirs = set()
    test_dir_names = ["tests", "test", "testing", "unit_tests", "integration_tests"]

    logger.debug(
        {
            "event": "searching_test_directories",
            "project_dir": str(project_dir),
            "looking_for": test_dir_names,
        }
    )

    # First check root directory for test files
    if _has_test_files(project_dir, env):
        test_dirs.add(project_dir)

    # Then walk subdirectories
    for root, dirs, _ in os.walk(project_dir):
        root_path = Path(root)

        matched_dirs = [d for d in dirs if d.lower() in test_dir_names]
        if matched_dirs:
            logger.debug(
                {
                    "event": "found_test_dir_names",
                    "root": str(root_path),
                    "matches": matched_dirs,
                }
            )
            test_dirs.update(root_path / d for d in matched_dirs)

        test_file_dirs = [d for d in dirs if _has_test_files(root_path / d, env)]
        if test_file_dirs:
            logger.debug(
                {
                    "event": "found_dirs_with_test_files",
                    "root": str(root_path),
                    "matches": test_file_dirs,
                }
            )
            test_dirs.update(root_path / d for d in test_file_dirs)

    logger.debug(
        {
            "event": "test_directory_search_complete",
            "found_directories": [str(d) for d in test_dirs],
        }
    )

    return test_dirs


def detect_frameworks(env: Environment) -> List[FrameworkType]:
    """Detect test frameworks in a project directory."""
    logger.info({"event": "framework_detection_start", "project_dir": str(env.sandbox.work_dir)})

    # Check for installed test runners based on runtime
    if env.runtime_config.name == Runtime.PYTHON:
        # Check if pytest is available on system path since we haven't installed it yet
        import shutil
        if shutil.which("pytest") and _find_test_dirs(env.sandbox.work_dir, env):
            logger.info({"event": "framework_detected", "framework": "pytest"})
            return [FrameworkType.PYTEST]
    
    # Add other runtimes here as needed
    
    logger.info({"event": "no_frameworks_detected"})
    return []


async def run_pytest(env: Environment) -> dict[str, Any]:
    """Run pytest in the environment."""
    result: dict[str, Any] = {"framework": FrameworkType.PYTEST.value}

    test_bin = env.sandbox.bin_dir / "pytest"
    pytest_cmd = f"{test_bin} -vv --no-header --json-report"

    test_dirs = _find_test_dirs(env.sandbox.work_dir, env)
    if not test_dirs:
        raise RuntimeError("No test directories found")

    all_results = []

    for test_dir in test_dirs:
        process = await run_sandboxed_command(
            env.sandbox,
            f"{pytest_cmd} {test_dir}",
            env.sandbox.env_vars,
        )
        stdout, stderr = await process.communicate()

        try:
            report = json.loads(stdout)
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

    return result



async def run_framework_tests(config: RunConfig) -> Dict[str, Any]:
    """Run tests for a specific framework in the environment"""
    logger.info({
        "event": "framework_test_start",
        "framework": config.framework.value,
        "working_dir": str(config.env.sandbox.work_dir),
    })

    match config.framework:
        case FrameworkType.PYTEST:
            result = await run_pytest(config.env)
        case _:
            error = f"Unsupported framework: {config.framework}"
            logger.error({"event": "framework_test_error", "error": error})
            raise ValueError(error)

    logger.info(
        {
            "event": "framework_test_complete",
            "framework": config.framework.value,
            "success": result.get("success", False),
        }
    )

    return result
