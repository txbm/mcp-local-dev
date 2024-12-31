"""Test execution utilities."""

import logging
from typing import Dict, Any

from mcp_runtime_server.commands import run_command
from mcp_runtime_server.managers import build_install_command, prepare_env_vars
from mcp_runtime_server.testing.frameworks import detect_frameworks, run_framework_tests
from mcp_runtime_server.types import Environment

logger = logging.getLogger(__name__)

async def install_dependencies(env: Environment) -> None:
    """Install project dependencies."""
    if not env.manager:
        raise RuntimeError("No runtime manager detected")

    logger.debug("Installing dependencies", extra={"env_id": env.id})
    cmd, args = build_install_command(env.manager)
    env_vars = prepare_env_vars(env.manager, env.env_vars)
    command = f"{cmd} {' '.join(args)}"

    process = await run_command(command, str(env.work_dir), env_vars)
    stdout, stderr = await process.communicate()

    logger.debug(
        "Dependency installation completed",
        extra={
            "command": command,
            "cwd": str(env.work_dir),
            "env": env_vars,
            "stdout": stdout.decode() if stdout else None,
            "stderr": stderr.decode() if stderr else None,
            "exit_code": process.returncode
        }
    )

    if process.returncode != 0:
        raise RuntimeError(f"Failed to install dependencies: {stderr.decode()}")

async def auto_run_tests(env: Environment) -> Dict[str, Any]:
    """Auto-detect and run tests."""
    try:
        logger.debug("Starting test execution", extra={"env_id": env.id})
        
        await install_dependencies(env)
        logger.debug("Dependencies installed successfully", extra={"env_id": env.id})
        
        frameworks = detect_frameworks(str(env.work_dir))
        logger.debug(
            "Test frameworks detected",
            extra={
                "env_id": env.id,
                "test_info": {
                    "frameworks": [f.value for f in frameworks]
                }
            }
        )
        
        if not frameworks:
            logger.warning("No test frameworks detected", extra={"env_id": env.id})
            return {
                "success": False,
                "frameworks": [],
                "error": "No test frameworks detected"
            }

        results = []
        overall_success = True
        
        for framework in frameworks:
            logger.debug(
                "Running tests for framework",
                extra={
                    "env_id": env.id,
                    "test_info": {"framework": framework.value}
                }
            )
            
            result = await run_framework_tests(framework, env)
            results.append(result)
            
            if not result.get("success", False):
                overall_success = False
                
            logger.debug(
                "Framework test execution completed",
                extra={
                    "env_id": env.id,
                    "test_info": {
                        "framework": framework.value,
                        "result": result
                    }
                }
            )

        return {
            "success": overall_success,
            "frameworks": results
        }

    except Exception as e:
        logger.exception(
            "Test execution failed",
            extra={
                "env_id": env.id,
                "error": str(e)
            }
        )
        return {
            "success": False,
            "frameworks": [],
            "error": str(e)
        }
