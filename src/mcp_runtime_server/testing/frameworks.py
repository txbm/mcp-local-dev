"""Test framework detection and configuration."""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


@dataclass(frozen=True)
class Framework:
    """Test framework configuration."""
    name: str
    run_command: str
    file_patterns: Tuple[str, ...]  # Changed from List to Tuple
    config_files: Tuple[str, ...]   # Changed from List to Tuple
    result_parser: str


# Framework definitions with their detection rules
FRAMEWORKS = {
    # JavaScript/Node.js
    "jest": Framework(
        name="jest",
        run_command="jest",
        file_patterns=("*.test.js", "*.spec.js"),  # Changed to tuple
        config_files=("jest.config.js", "package.json"),  # Changed to tuple
        result_parser="jest"
    ),
    "mocha": Framework(
        name="mocha",
        run_command="mocha",
        file_patterns=("test/*.js", "*.test.js", "*.spec.js"),  # Changed to tuple
        config_files=(".mocharc.js", ".mocharc.json", "package.json"),  # Changed to tuple
        result_parser="mocha"
    ),
    "vitest": Framework(
        name="vitest",
        run_command="vitest",
        file_patterns=("*.test.ts", "*.spec.ts"),  # Changed to tuple
        config_files=("vitest.config.ts", "vite.config.ts"),  # Changed to tuple
        result_parser="vitest"
    ),

    # Python
    "pytest": Framework(
        name="pytest",
        run_command="pytest",
        file_patterns=("test_*.py", "*_test.py"),  # Changed to tuple
        config_files=("pytest.ini", "pyproject.toml", "setup.cfg"),  # Changed to tuple
        result_parser="pytest"
    ),
    "unittest": Framework(
        name="unittest",
        run_command="python -m unittest discover",
        file_patterns=("test_*.py", "*_test.py"),  # Changed to tuple
        config_files=("unittest.cfg",),  # Changed to tuple with comma
        result_parser="unittest"
    ),

    # Rust
    "cargo-test": Framework(
        name="cargo-test",
        run_command="cargo test",
        file_patterns=("**/tests/*.rs",),  # Changed to tuple with comma
        config_files=("Cargo.toml",),  # Changed to tuple with comma
        result_parser="cargo-test"
    ),

    # Go
    "go-test": Framework(
        name="go-test",
        run_command="go test",
        file_patterns=("*_test.go",),  # Changed to tuple with comma
        config_files=("go.mod",),  # Changed to tuple with comma
        result_parser="go-test"
    )
}


def detect_frameworks(working_dir: str) -> List[Framework]:
    """Detect test frameworks in a project directory.
    
    Args:
        working_dir: Project directory to examine
        
    Returns:
        List of detected frameworks
    """
    try:
        path = Path(working_dir)
        detected = set()

        # Check for config files
        all_files = set(str(p) for p in path.rglob("*"))
        
        for framework in FRAMEWORKS.values():
            # Look for config files
            for config in framework.config_files:
                if any(f.endswith(config) for f in all_files):
                    detected.add(framework)
                    break
                    
            # Look for test files matching patterns
            if not framework in detected:
                for pattern in framework.file_patterns:
                    if any(path.rglob(pattern)):
                        detected.add(framework)
                        break
        
        return list(detected)
        
    except Exception as e:
        raise RuntimeError(f"Failed to detect frameworks: {e}")


def get_framework_command(
    framework: Framework,
    working_dir: str
) -> Tuple[str, Dict[str, str]]:
    """Get the appropriate test command for a framework.
    
    Args:
        framework: Framework to get command for
        working_dir: Project directory
        
    Returns:
        Tuple of (command, environment variables)
    """
    try:
        env_vars = {}
        command = framework.run_command

        if framework.name == "jest":
            # Check for jest binary in node_modules
            jest_bin = Path(working_dir) / "node_modules" / ".bin" / "jest"
            if jest_bin.exists():
                command = str(jest_bin)
            env_vars["NODE_ENV"] = "test"

        elif framework.name == "pytest":
            # Add coverage and verbose output by default
            command = f"{command} -v --cov"
            
        elif framework.name == "cargo-test":
            # Add color output
            command = f"{command} --color always"
            
        return command, env_vars
        
    except Exception as e:
        raise RuntimeError(f"Failed to get framework command: {e}")


def parse_test_results(
    framework: Framework,
    stdout: str,
    stderr: str,
    exit_code: int
) -> Dict[str, Any]:
    """Parse framework-specific test output.
    
    Args:
        framework: Framework that generated the output
        stdout: Standard output from test run
        stderr: Standard error from test run
        exit_code: Process exit code
        
    Returns:
        Dict containing parsed test results
    """
    try:
        if framework.name == "jest":
            return _parse_jest_output(stdout)
        elif framework.name == "pytest":
            return _parse_pytest_output(stdout)
        elif framework.name == "cargo-test":
            return _parse_cargo_test_output(stdout)
        elif framework.name == "go-test":
            return _parse_go_test_output(stdout)
        else:
            # Basic parsing for unknown frameworks
            return {
                "success": exit_code == 0,
                "output": stdout,
                "errors": stderr if stderr else None
            }
            
    except Exception as e:
        raise RuntimeError(f"Failed to parse test results: {e}")


def _parse_jest_output(output: str) -> Dict[str, Any]:
    """Parse Jest test output."""
    results = {
        "passed": 0,
        "failed": 0,
        "total": 0,
        "failures": []
    }
    
    for line in output.splitlines():
        if "Test Suites:" in line:
            parts = line.split(",")
            for part in parts:
                if "failed" in part:
                    results["failed"] = int(part.split()[0])
                elif "passed" in part:
                    results["passed"] = int(part.split()[0])
                elif "total" in part:
                    results["total"] = int(part.split()[0])
                    
        elif "FAIL" in line and "●" in line:
            results["failures"].append(line.strip())
            
    return results


def _parse_pytest_output(output: str) -> Dict[str, Any]:
    """Parse pytest output."""
    results = {
        "passed": 0,
        "failed": 0,
        "total": 0,
        "failures": [],
        "coverage": None
    }
    
    for line in output.splitlines():
        if "failed" in line and "passed" in line:
            # Parse test summary line
            parts = line.split()
            for part in parts:
                if "passed" in part:
                    results["passed"] = int(part.split("passed")[0])
                elif "failed" in part:
                    results["failed"] = int(part.split("failed")[0])
                    
        elif "FAILED" in line and "::" in line:
            results["failures"].append(line.strip())
            
        elif "TOTAL" in line and "%" in line:
            # Parse coverage information
            try:
                coverage = int(line.split("%")[0].split()[-1])
                results["coverage"] = coverage
            except (ValueError, IndexError):
                pass
                
    results["total"] = results["passed"] + results["failed"]
    return results


def _parse_cargo_test_output(output: str) -> Dict[str, Any]:
    """Parse Cargo test output."""
    results = {
        "passed": 0,
        "failed": 0,
        "total": 0,
        "failures": []
    }
    
    for line in output.splitlines():
        if "test result:" in line:
            parts = line.split(".")
            for part in parts:
                if "passed" in part:
                    results["passed"] = int(part.split()[0])
                elif "failed" in part:
                    results["failed"] = int(part.split()[0])
                    
        elif "failures:" in line:
            results["failures"].append(line.strip())
            
    results["total"] = results["passed"] + results["failed"]
    return results


def _parse_go_test_output(output: str) -> Dict[str, Any]:
    """Parse Go test output."""
    results = {
        "passed": 0,
        "failed": 0,
        "total": 0,
        "failures": []
    }
    
    for line in output.splitlines():
        if line.startswith("ok") or line.startswith("FAIL"):
            parts = line.split()
            if "ok" in line:
                results["passed"] += 1
            else:
                results["failed"] += 1
                results["failures"].append(line.strip())
                
    results["total"] = results["passed"] + results["failed"]
    return results