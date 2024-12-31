"""Test execution module."""
import asyncio
import json
from typing import List

import mcp.types as types
from mcp_runtime_server.environments import Environment
from mcp_runtime_server.testing.frameworks import (
    detect_frameworks,
    run_framework_tests,
    TestFramework
)
from mcp_runtime_server.logging import get_logger, format_test_results

logger = get_logger("testing.execution")

async def auto_run_tests(env: Environment) -> List[types.TextContent]:
    """Auto-detect and run tests in the environment."""
    try:
        frameworks = detect_frameworks(str(env.work_dir))
        if not frameworks:
            return [types.TextContent(
                text=json.dumps({
                    "success": False,
                    "error": "No test frameworks detected"
                }),
                type="text"
            )]
        
        results = []
        for framework in frameworks:
            result = await run_framework_tests(framework, env)
            results.append(result)
        
        all_passed = all(r.get("success", False) for r in results)
        return format_test_results(frameworks[0].value, results[0] if results else {})

    except Exception as e:
        logger.exception("Test execution failed")
        return [types.TextContent(
            text=json.dumps({
                "success": False,
                "error": str(e)
            }),
            type="text"
        )]