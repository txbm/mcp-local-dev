"""Test execution and management."""
import asyncio
import psutil
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

from .types import (
    TestConfig,
    TestResult,
    TestRunResult,
    CapturedOutput,
    RuntimeEnv
)
from .sandbox import create_sandbox, cleanup_sandbox
from .binaries import ensure_binary
from .frameworks import (
    detect_frameworks,
    get_framework_command,
    parse_test_results,
    TestFramework
)


async def auto_detect_and_run_tests(
    env: RuntimeEnv,
    include_coverage: bool = True,
    parallel: bool = False
) -> Dict[str, Any]:
    """Auto-detect and run tests in an environment.
    
    Args:
        env: Runtime environment
        include_coverage: Include coverage reporting if available
        parallel: Run tests in parallel if supported
        
    Returns:
        Dict containing test results and framework info
    """
    # Create sandbox for test execution
    sandbox = create_sandbox(base_env=env.env_vars)
    start_time = datetime.now()
    
    try:
        # Copy project files to sandbox
        src_root = Path(env.working_dir)
        for item in src_root.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(src_root)
                dst_path = sandbox.root / rel_path
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                dst_path.write_bytes(item.read_bytes())
                
        # Set up test environment
        frameworks = detect_frameworks(str(sandbox.root))
        if not frameworks:
            return {
                "error": "No test frameworks detected",
                "working_dir": str(sandbox.root)
            }
        
        results = {}
        total_tests = 0
        total_passed = 0
        total_failed = 0
        
        for framework in frameworks:
            # Get framework command
            command, framework_env = get_framework_command(
                framework,
                str(sandbox.root)
            )
            
            # Add framework binary to sandbox
            bin_path = await ensure_binary(framework.name)
            if bin_path:
                dest = sandbox.bin_dir / bin_path.name
                dest.write_bytes(bin_path.read_bytes())
                dest.chmod(0o755)
            
            # Add coverage flags
            if include_coverage:
                if framework.name == "jest":
                    command += " --coverage"
                elif framework.name == "pytest":
                    command += " --cov"
            
            # Add parallel execution if supported
            if parallel:
                if framework.name == "jest":
                    command += " --maxWorkers=50%"
                elif framework.name == "pytest":
                    command += " -n auto"
                elif framework.name == "cargo-test":
                    command += " -- --test-threads=num_cpus"
            
            # Run tests
            test_env = sandbox.env_vars.copy()
            test_env.update(framework_env)
            
            framework_start = datetime.now()
            process = await asyncio.create_subprocess_shell(
                command,
                env=test_env,
                cwd=str(sandbox.root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            framework_end = datetime.now()
            
            stdout_str = stdout.decode() if stdout else ""
            stderr_str = stderr.decode() if stderr else ""
            
            # Parse results
            framework_results = parse_test_results(
                framework,
                stdout_str,
                stderr_str,
                process.returncode
            )
            
            # Add execution info
            framework_results.update({
                "framework": framework.name,
                "command": command,
                "execution_time": (framework_end - framework_start).total_seconds(),
                "exit_code": process.returncode,
                "output": {
                    "stdout": stdout_str,
                    "stderr": stderr_str
                }
            })
            
            # Update totals
            total_tests += framework_results.get("total", 0)
            total_passed += framework_results.get("passed", 0)
            total_failed += framework_results.get("failed", 0)
            
            results[framework.name] = framework_results
            
        end_time = datetime.now()
        
        return {
            "results": results,
            "summary": {
                "frameworks_detected": len(frameworks),
                "frameworks_run": len(results),
                "all_passed": total_failed == 0,
                "total_tests": total_tests,
                "total_passed": total_passed,
                "total_failed": total_failed,
                "total_time": (end_time - start_time).total_seconds()
            }
        }
        
    finally:
        # Clean up sandbox
        cleanup_sandbox(sandbox)


async def run_test(
    env_id: str,
    config: TestConfig
) -> TestRunResult:
    """Run a single test in a sandbox.
    
    Args:
        env_id: Environment identifier
        config: Test configuration
        
    Returns:
        TestRunResult with test execution results
    """
    # Create sandbox for test execution
    sandbox = create_sandbox()
    
    try:
        process = await asyncio.create_subprocess_shell(
            config.command,
            env=sandbox.env_vars,
            cwd=str(sandbox.root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=config.timeout_seconds
            )
            
            captured = CapturedOutput(
                stdout=stdout.decode() if stdout else "",
                stderr=stderr.decode() if stderr else "",
                exit_code=process.returncode,
                start_time=datetime.fromtimestamp(
                    psutil.Process(process.pid).create_time()
                ),
                end_time=datetime.now()
            )
            
            # Check exit code
            if captured.exit_code != config.expected_exit_code:
                return TestRunResult(
                    config=config,
                    result=TestResult.FAIL,
                    captured=captured,
                    error_message=(
                        f"Expected exit code {config.expected_exit_code}, "
                        f"got {captured.exit_code}"
                    ),
                    failure_details={
                        "expected_exit_code": str(config.expected_exit_code),
                        "actual_exit_code": str(captured.exit_code)
                    }
                )
            
            # Check expected output if specified
            if config.expected_output:
                if config.expected_output not in captured.stdout:
                    return TestRunResult(
                        config=config,
                        result=TestResult.FAIL,
                        captured=captured,
                        error_message="Expected output not found in stdout",
                        failure_details={
                            "expected_output": config.expected_output,
                            "actual_output": captured.stdout
                        }
                    )
            
            return TestRunResult(
                config=config,
                result=TestResult.PASS,
                captured=captured
            )
            
        except asyncio.TimeoutError:
            return TestRunResult(
                config=config,
                result=TestResult.TIMEOUT,
                captured=CapturedOutput(
                    stdout="",
                    stderr="Test timed out",
                    exit_code=-1,
                    start_time=datetime.fromtimestamp(
                        psutil.Process(process.pid).create_time()
                    ),
                    end_time=datetime.now()
                ),
                error_message=f"Test timed out after {config.timeout_seconds}s"
            )
        
    except Exception as e:
        return TestRunResult(
            config=config,
            result=TestResult.ERROR,
            captured=CapturedOutput(
                stdout="",
                stderr=str(e),
                exit_code=-1,
                start_time=datetime.now(),
                end_time=datetime.now()
            ),
            error_message=f"Test execution error: {str(e)}"
        )
        
    finally:
        cleanup_sandbox(sandbox)


async def run_tests(
    env_id: str,
    configs: List[TestConfig],
    parallel: bool = False,
    max_concurrent: Optional[int] = None
) -> Dict[str, TestRunResult]:
    """Run multiple tests in sandboxed environments.
    
    Args:
        env_id: Environment identifier
        configs: List of test configurations
        parallel: Run tests in parallel if True
        max_concurrent: Maximum number of concurrent test runs
        
    Returns:
        Dict mapping test names to their results
    """
    results: Dict[str, TestRunResult] = {}
    
    if parallel:
        # Run tests in parallel with optional concurrency limit
        semaphore = asyncio.Semaphore(max_concurrent or len(configs))
        
        async def run_with_semaphore(config: TestConfig):
            async with semaphore:
                return await run_test(env_id, config)
        
        # Create and gather all test tasks
        tasks = [
            asyncio.create_task(run_with_semaphore(config))
            for config in configs
        ]
        test_results = await asyncio.gather(*tasks)
        
        # Map results to test names
        results = {
            result.config.name: result
            for result in test_results
        }
        
    else:
        # Run tests sequentially
        for config in configs:
            results[config.name] = await run_test(env_id, config)
    
    return results