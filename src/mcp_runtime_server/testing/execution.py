"""Test execution module."""
import asyncio
from typing import List

import mcp.types as types
import json

from mcp_runtime_server.environments import Environment
from mcp_runtime_server.managers import detect_manager, prepare_environment
from mcp_runtime_server.testing.validation import validate_test_results
from mcp_runtime_server.logging import get_logger, parse_pytest_output

logger = get_logger("testing.execution")

async def auto_run_tests(env: Environment) -> List[types.TextContent]:
    """Auto-detect and run tests in the environment."""
    try:
        manager = detect_manager(env.manager)
        if not manager:
            return [types.TextContent(
                text=json.dumps({
                    "success": False,
                    "error": "No suitable test manager found"
                }),
                type="text"
            )]

        await prepare_environment(env)
        
        # Run pytest
        process = await asyncio.create_subprocess_exec(
            "uv", "run", "pytest",
            cwd=env.work_dir,
            env=env.env_vars,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout_bytes, stderr_bytes = await process.communicate()
        stdout = stdout_bytes.decode() if stdout_bytes else ""
        stderr = stderr_bytes.decode() if stderr_bytes else ""

        if process.returncode not in (0, 1):  # 1 is test failures
            return [types.TextContent(
                text=json.dumps({
                    "success": False,
                    "error": f"Pytest failed with code {process.returncode}",
                    "stdout": stdout,
                    "stderr": stderr
                }),
                type="text"
            )]

        # Parse and validate results
        results = parse_pytest_output(stdout, stderr)
        frameworks = [{
            "framework": "pytest",
            **results
        }]
        
        return [types.TextContent(
            text=json.dumps({"success": True, "frameworks": frameworks}),
            type="text"
        )]

    except Exception as e:
        logger.exception("Test execution failed")
        return [types.TextContent(
            text=json.dumps({
                "success": False,
                "error": str(e)
            }),
            type="text"
        )]