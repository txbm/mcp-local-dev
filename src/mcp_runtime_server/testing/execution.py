"""Test execution and result handling."""
from typing import Dict, Any
from pathlib import Path

from mcp_runtime_server.types import Environment
from mcp_runtime_server.commands import run_command
from mcp_runtime_server.testing.frameworks import detect_frameworks, get_framework_command, parse_test_results


async def auto_run_tests(env: Environment) -> Dict[str, any]:
    """Auto-detect and run tests."""
    try:
        # Auto-detect test frameworks
        frameworks = detect_frameworks(env.work_dir)
        if not frameworks:
            return {"error": "No test frameworks detected"}
            
        results = []
        for framework in frameworks:
            # Get framework-specific command
            command, extra_env = get_framework_command(framework, env.work_dir)
            
            # Update environment variables
            env_vars = env.env_vars.copy()
            env_vars.update(extra_env)
            
            # Run tests
            process = await run_command(command, env.work_dir, env_vars)
            stdout, stderr = await process.communicate()
            
            # Parse results
            framework_results = parse_test_results(
                framework,
                stdout.decode() if stdout else "",
                stderr.decode() if stderr else "",
                process.returncode
            )
            
            results.append({
                "framework": framework.name,
                **framework_results
            })
            
        return {
            "success": all(r.get("success", False) for r in results),
            "frameworks": results
        }

    except Exception as e:
        return {"success": False, "error": str(e)}