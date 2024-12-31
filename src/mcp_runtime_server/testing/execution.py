"""Test execution module."""
import json
import logging
from typing import List

import mcp.types as types
from mcp_runtime_server.environments import Environment
from mcp_runtime_server.testing.frameworks import (
    detect_frameworks,
    run_framework_tests,
    TestFramework
)
from mcp_runtime_server.testing.results import format_test_results

logger = logging.getLogger("mcp_runtime_server.testing.execution")

async def auto_run_tests(env: Environment) -> List[types.TextContent]:
    """Auto-detect and run tests in the environment."""
    try:
        frameworks = detect_frameworks(str(env.work_dir))
        if not frameworks:
            logger.info("No test frameworks detected", extra={
                'data': {'work_dir': str(env.work_dir)}
            })
            return [types.TextContent(
                text=json.dumps({
                    "success": False,
                    "error": "No test frameworks detected"
                }),
                type="text"
            )]
        
        results = []
        for framework in frameworks:
            logger.info("Running tests", extra={
                'data': {
                    'framework': framework.value,
                    'work_dir': str(env.work_dir)
                }
            })
            result = await run_framework_tests(framework, env)
            results.append(result)
            
        all_passed = all(r.get("success", False) for r in results)
        logger.info("Test execution complete", extra={
            'data': {
                'all_passed': all_passed,
                'total_frameworks': len(frameworks)
            }
        })
        return format_test_results(frameworks[0].value, results[0] if results else {})

    except Exception as e:
        logger.error("Test execution failed", extra={
            'data': {
                'error': str(e),
                'work_dir': str(env.work_dir)
            }
        })
        return [types.TextContent(
            text=json.dumps({
                "success": False,
                "error": str(e)
            }),
            type="text"
        )]