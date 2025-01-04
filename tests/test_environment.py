import pytest
from pathlib import Path

from mcp_runtime_server.environments.environment import create_environment
from mcp_runtime_server.types import Runtime

@pytest.mark.asyncio
async def test_create_environment_from_python_project():
    """Test creating environment from real Python project"""
    # Use this repo as test project
    project_path = Path(__file__).parent.parent
    
    env = await create_environment(project_path)
    assert env.runtime_config.name == Runtime.PYTHON
    assert env.sandbox.work_dir.exists()
    assert (env.sandbox.work_dir / "pyproject.toml").exists()
    
    # Cleanup
    env.sandbox.temp_dir.cleanup()

@pytest.mark.asyncio 
async def test_create_environment_from_github():
    """Test creating environment from GitHub repo"""
    from mcp_runtime_server.environments.environment import create_environment_from_github
    from mcp_runtime_server.sandboxes.sandbox import create_sandbox
    
    staging = await create_sandbox("staging-")
    try:
        env = await create_environment_from_github(
            staging,
            "https://github.com/pytest-dev/pytest",
            "main"
        )
        assert env.runtime_config.name == Runtime.PYTHON
        assert env.sandbox.work_dir.exists()
        assert (env.sandbox.work_dir / "setup.py").exists()
        
        # Cleanup
        env.sandbox.temp_dir.cleanup()
    finally:
        staging.temp_dir.cleanup()
