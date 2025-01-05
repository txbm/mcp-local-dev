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
    assert env.runtime_config.name == Runtime.PYTHON
    assert env.sandbox.work_dir.exists()
    assert (env.sandbox.work_dir / "pyproject.toml").exists()
    
    # Cleanup
    env.sandbox.temp_dir.cleanup()

@pytest.mark.asyncio 
async def test_create_environment_from_github():
    """Test creating environment from GitHub repo"""
    from mcp_local_dev.environments.environment import create_environment_from_github
    from mcp_runtime_server.sandboxes.sandbox import create_sandbox
    
    staging = await create_sandbox("staging-")
    try:
        env = await create_environment_from_github(
            staging,
            "https://github.com/pallets/flask",
            "main"
        )
        assert env.runtime_config.name == Runtime.PYTHON
        assert env.sandbox.work_dir.exists()
        assert (env.sandbox.work_dir / "pyproject.toml").exists()
        
        # Cleanup
        env.sandbox.temp_dir.cleanup()
    finally:
        staging.temp_dir.cleanup()
