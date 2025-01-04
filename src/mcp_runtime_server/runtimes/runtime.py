"""Runtime detection and configuration."""

from typing import Dict

from mcp_runtime_server.types import Runtime, PackageManager, RuntimeConfig, Sandbox
from mcp_runtime_server.logging import get_logger

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
    logger.debug({"event": "detecting_runtime", "work_dir": str(work_dir)})

    files = set(str(p) for p in work_dir.rglob("*"))
    logger.debug({"event": "found_project_files", "files": list(files)})

    for runtime, config in RUNTIME_CONFIGS.items():
        if runtime == Runtime.BUN:
            if all(any(f.endswith(c) for f in files) for c in config.config_files):
                logger.info(
                    {
                        "event": "runtime_detected",
                        "runtime": runtime.value,
                        "matched_files": config.config_files,
                    }
                )
                return config
        else:
            if any(any(f.endswith(c) for f in files) for c in config.config_files):
                matched_file = next(
                    c for c in config.config_files if any(f.endswith(c) for f in files)
                )
                logger.info(
                    {
                        "event": "runtime_detected",
                        "runtime": runtime.value,
                        "matched_file": matched_file,
                        "files_checked": config.config_files,
                    }
                )
                return config

    logger.error(
        {
            "event": "no_runtime_detected",
            "work_dir": str(work_dir),
            "files_found": list(files),
        }
    )
    raise ValueError("No supported runtime detected")


async def install_runtime(
    sandbox: Sandbox, config: RuntimeConfig
) -> None:
    """Install runtime assuming binaries are on system path"""
    import shutil
    from mcp_runtime_server.sandboxes.sandbox import run_sandboxed_command
    
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
        
    # Add package manager bin path to sandbox PATH
    from mcp_runtime_server.sandboxes.sandbox import update_sandbox_path
    update_sandbox_path(sandbox, config.package_manager)
    
