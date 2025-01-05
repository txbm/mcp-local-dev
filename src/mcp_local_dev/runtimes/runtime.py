"""Runtime detection and configuration."""

from typing import Dict

from mcp_local_dev.types import Runtime, PackageManager, RuntimeConfig, Sandbox
from mcp_local_dev.logging import get_logger

logger = get_logger(__name__)


RUNTIME_CONFIGS: Dict[Runtime, RuntimeConfig] = {
    Runtime.NODE: RuntimeConfig(
        name=Runtime.NODE,
        config_files=["package.json"],
        package_manager=PackageManager.NPM,
        env_setup={"NODE_NO_WARNINGS": "1"},
        binary_name="node",
    ),
    Runtime.BUN: RuntimeConfig(
        name=Runtime.BUN,
        config_files=["bun.lockb", "package.json"],
        package_manager=PackageManager.BUN,
        env_setup={"NO_INSTALL_HINTS": "1"},
        binary_name="bun",
    ),
    Runtime.PYTHON: RuntimeConfig(
        name=Runtime.PYTHON,
        config_files=["pyproject.toml", "setup.py", "requirements.txt"],
        package_manager=PackageManager.UV,
        env_setup={
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        binary_name="python",
    ),
}


def detect_runtime(sandbox: Sandbox) -> RuntimeConfig:
    """Detect runtime from project files."""
    work_dir = sandbox.work_dir
    
    SKIP_DIRS = {'.git', '.svn', '.hg', '.pytest_cache', '__pycache__', 'node_modules', '.venv'}
    
    files = {
        str(p.relative_to(work_dir))
        for p in work_dir.rglob("*")
        if not any(part.startswith('.') or part in SKIP_DIRS for part in p.parts)
    }

    for runtime, config in RUNTIME_CONFIGS.items():
        if any(any(f.endswith(c) for f in files) for c in config.config_files):
            return config

    raise ValueError("No supported runtime detected")


async def install_runtime(
    sandbox: Sandbox, config: RuntimeConfig
) -> None:
    """Install runtime assuming binaries are on system path"""
    import shutil
    from mcp_local_dev.sandboxes.sandbox import run_sandboxed_command
    
    # Verify required binaries exist
    required_binaries = [config.binary_name]
    pkg_bin = sandbox.bin_dir / config.package_manager.name.lower()
    runtime_bin = sandbox.bin_dir / config.binary_name
    
    if config.package_manager == PackageManager.UV:
        required_binaries.append('uv')
    elif config.package_manager == PackageManager.NPM:
        required_binaries.append('npm')
    elif config.package_manager == PackageManager.BUN:
        required_binaries.append('bun')
        
    missing = [bin for bin in required_binaries if not shutil.which(bin)]
    if missing:
        raise RuntimeError(f"Required binaries not found: {', '.join(missing)}")
        
    # Set up environment variables
    for key, value in config.env_setup.items():
        sandbox.env_vars[key] = value
        
