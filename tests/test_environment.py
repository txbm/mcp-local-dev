import pytest
import tempfile
import shutil
import tomli
from pathlib import Path

from mcp_local_dev.environments.environment import create_environment, cleanup_environment
from mcp_local_dev.types import Runtime
from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command

@pytest.mark.asyncio
async def test_create_environment_from_python_project(tmp_path: Path):
    """Test creating environment from real Python project"""
    # Copy pytest fixture project
    fixture_dir = Path(__file__).parent.parent / "fixtures_data" / "python" / "pytest-project"
    project_dir = tmp_path / "pytest-project"
    shutil.copytree(fixture_dir, project_dir)
    
    env = await create_environment(project_dir)
    try:
        assert env.runtime_config.name == Runtime.PYTHON
        assert env.sandbox.work_dir.exists()
        assert (env.sandbox.work_dir / "pyproject.toml").exists()
        assert (env.sandbox.work_dir / "tests").exists()
        assert (env.sandbox.work_dir / "src").exists()

        # Read package name from pyproject.toml
        with open(project_dir / "pyproject.toml", "rb") as f:
            pyproject = tomli.load(f)
        package_name = pyproject["project"]["name"]

        # Verify Python works and can import project
        returncode, stdout, _ = await run_sandboxed_command(
            env.sandbox,
            f"python -c 'import {package_name}; print({package_name}.__name__)'")
        assert returncode == 0
        assert stdout.decode().strip() == package_name
    finally:
        cleanup_environment(env)

@pytest.mark.asyncio
async def test_cleanup_environment(tmp_path: Path):
    """Test environment cleanup"""
    # Copy pytest fixture project
    fixture_dir = Path(__file__).parent.parent / "fixtures_data" / "python" / "pytest-project"
    project_dir = tmp_path / "pytest-project"
    shutil.copytree(fixture_dir, project_dir)
    
    env = await create_environment(project_dir)
    work_dir = env.sandbox.work_dir
    assert work_dir.exists()
    assert (work_dir / "pyproject.toml").exists()
    
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
            "https://github.com/txbm/mcp-python-repo-fixture",
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
