import pytest
import tempfile
from pathlib import Path

from mcp_local_dev.environments.environment import create_environment
from mcp_local_dev.types import Runtime

@pytest.mark.asyncio
async def test_create_environment_from_python_project():
    """Test creating environment from real Python project"""
    # Create temp dir with minimal Python project
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_dir = Path(tmp_dir)
        (project_dir / "pyproject.toml").write_text("""
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "test-project"
version = "0.1.0"
        """)
        
        env = await create_environment(project_dir)
        try:
            assert env.runtime_config.name == Runtime.PYTHON
            assert env.sandbox.work_dir.exists()
            assert (env.sandbox.work_dir / "pyproject.toml").exists()

            # Verify Python works
            process = await run_sandboxed_command(
                env.sandbox,
                "python -c 'print(\"test\")'")
            stdout, _ = await process.communicate()
            assert process.returncode == 0
            assert stdout.decode().strip() == "test"
        finally:
            cleanup_environment(env)

@pytest.mark.asyncio
async def test_cleanup_environment():
    """Test environment cleanup"""
    env = await create_environment(Path.cwd())
    work_dir = env.sandbox.work_dir
    assert work_dir.exists()
    
    cleanup_environment(env)
    assert not work_dir.exists()

@pytest.mark.asyncio 
async def test_create_environment_from_github():
    """Test creating environment from GitHub repo"""
    from mcp_local_dev.environments.environment import create_environment_from_github 
    from mcp_local_dev.sandboxes.sandbox import create_sandbox
    
    staging = await create_sandbox("staging-")
    try:
        env = await create_environment_from_github(
            staging,
            "https://github.com/pallets/flask",
            "main"
        )
        try:
            assert env.runtime_config.name == Runtime.PYTHON
            assert env.sandbox.work_dir.exists()
            assert (env.sandbox.work_dir / "pyproject.toml").exists()
        finally:
            env.sandbox.temp_dir.cleanup()
    finally:
        staging.temp_dir.cleanup()
