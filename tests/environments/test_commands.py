"""Tests for environment command execution."""
import pytest
from pathlib import Path

from mcp_runtime_server.environments.environment import create_environment
from mcp_runtime_server.environments.runtime import Runtime
from mcp_runtime_server.environments.commands import run_command, run_install

async def test_run_install_node(tmp_path):
    """Test running install for Node.js environment."""
    env = await create_environment(tmp_path, "https://github.com/username/node-project")
    pkg_json = env.work_dir / "package.json"
    pkg_json.write_text('{"name": "test", "version": "1.0.0"}')
    
    await run_install(env)
    assert (env.work_dir / "node_modules").exists()

async def test_run_install_python(tmp_path):
    """Test running install for Python environment."""
    env = await create_environment(tmp_path, "https://github.com/username/python-project")
    pyproject = env.work_dir / "pyproject.toml"
    pyproject.write_text('''[project]
name = "test"
version = "0.1.0"
''')
    
    await run_install(env)
    assert (env.work_dir / ".venv").exists()
    assert (env.work_dir / ".venv" / "bin" / "python").exists() or \
           (env.work_dir / ".venv" / "Scripts" / "python.exe").exists()

async def test_run_install_fails_no_config(tmp_path):
    """Test install failure without config files."""
    env = await create_environment(tmp_path, "https://github.com/username/empty-project")
    
    with pytest.raises(RuntimeError, match="Install failed"):
        await run_install(env)

async def test_run_command_captures_output(tmp_path):
    """Test command output capture."""
    env = await create_environment(tmp_path, "https://github.com/username/test-project")
    
    # Test echo command
    process = await run_command("echo 'test'" if os.name != 'nt' else "echo test", 
                              str(env.work_dir), env.env_vars)
    stdout, stderr = await process.communicate()
    
    assert process.returncode == 0
    assert stdout.decode().strip() == "test"