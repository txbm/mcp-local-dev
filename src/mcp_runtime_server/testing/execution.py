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
            logger.info(json.dumps({
                "event": "no_frameworks_detected",
                "working_dir": str(env.work_dir)
            }))
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
        logger.info(json.dumps({
            "event": "test_run_complete",
            "all_passed": all_passed,
            "framework_count": len(frameworks)
        }))
        return format_test_results(frameworks[0].value, results[0] if results else {})

    except Exception as e:
        logger.error(json.dumps({
            "event": "test_run_error",
            "error": str(e)
        }))
        return [types.TextContent(
            text=json.dumps({
                "success": False,
                "error": str(e)
            }),
            type="text"
        )]