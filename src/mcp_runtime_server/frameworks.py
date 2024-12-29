"""Test framework detection and configuration."""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

@dataclass(frozen=True)
class TestFramework:
    """Test framework configuration."""
    name: str
    run_command: str
    file_patterns: List[str]
    config_files: List[str]
    result_parser: str

# Framework definitions with their detection rules
FRAMEWORKS = {
    # JavaScript/Node.js
    "jest": TestFramework(
        name="jest",
        run_command="jest",
        file_patterns=["*.test.js", "*.spec.js"],
        config_files=["jest.config.js", "package.json"],
        result_parser="jest"
    ),
    "mocha": TestFramework(
        name="mocha",
        run_command="mocha",
        file_patterns=["test/*.js", "*.test.js", "*.spec.js"],
        config_files=[".mocharc.js", ".mocharc.json", "package.json"],
        result_parser="mocha"
    ),
    "vitest": TestFramework(
        name="vitest",
        run_command="vitest",
        file_patterns=["*.test.ts", "*.spec.ts"],
        config_files=["vitest.config.ts", "vite.config.ts"],
        result_parser="vitest"
    ),

    # Python
    "pytest": TestFramework(
        name="pytest",
        run_command="pytest",
        file_patterns=["test_*.py", "*_test.py"],
        config_files=["pytest.ini", "pyproject.toml", "setup.cfg"],
        result_parser="pytest"
    ),
    "unittest": TestFramework(
        name="unittest",
        run_command="python -m unittest discover",
        file_patterns=["test_*.py", "*_test.py"],
        config_files=["unittest.cfg"],
        result_parser="unittest"
    ),

    # Rust
    "cargo-test": TestFramework(
        name="cargo-test",
        run_command="cargo test",
        file_patterns=["**/tests/*.rs"],
        config_files=["Cargo.toml"],
        result_parser="cargo-test"
    ),

    # Go
    "go-test": TestFramework(
        name="go-test",
        run_command="go test",
        file_patterns=["*_test.go"],
        config_files=["go.mod"],
        result_parser="go-test"
    )
}


def detect_frameworks(working_dir: str) -> List[TestFramework]:
    """Detect test frameworks in a project directory.
    
    Args:
        working_dir: Project directory to examine
        
    Returns:
        List of detected test frameworks
    """
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


def get_framework_command(
    framework: TestFramework,
    working_dir: str
) -> Tuple[str, Dict[str, str]]:
    """Get the appropriate test command for a framework.
    
    Args:
        framework: Test framework to use
        working_dir: Project directory
        
    Returns:
        Tuple of (command, environment variables)
    """
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


def parse_test_results(
    framework: TestFramework,
    stdout: str,
    stderr: str,
    exit_code: int
) -> Dict[str, Any]:
    """Parse framework-specific test output.
    
    Args:
        framework: Test framework that generated the output
        stdout: Standard output from test run
        stderr: Standard error from test run
        exit_code: Process exit code
        
    Returns:
        Dict containing parsed test results
    """
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


# Framework-specific result parsers
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