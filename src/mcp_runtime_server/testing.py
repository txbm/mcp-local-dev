"""Test execution and management functions."""
import asyncio
from typing import List, Dict, Optional

from .types import (
    TestConfig,
    TestResult,
    TestRunResult,
    CapturedOutput
)
from .runtime import run_in_env


async def run_test(env_id: str, config: TestConfig) -> TestRunResult:
    """Run a single test in the specified environment.
    
    Args:
        env_id: Environment identifier
        config: Test configuration
        
    Returns:
        TestRunResult with test execution results
    """
    try:
        captured = await run_in_env(
            env_id=env_id,
            command=config.command,
            capture_config=config.capture_config
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
                start_time=captured.start_time if 'captured' in locals() else None,
                end_time=captured.end_time if 'captured' in locals() else None
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
                start_time=captured.start_time if 'captured' in locals() else None,
                end_time=captured.end_time if 'captured' in locals() else None
            ),
            error_message=f"Test execution error: {str(e)}"
        )


async def run_tests(
    env_id: str,
    configs: List[TestConfig],
    parallel: bool = False,
    max_concurrent: Optional[int] = None
) -> Dict[str, TestRunResult]:
    """Run multiple tests in the specified environment.
    
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