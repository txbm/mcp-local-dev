"""Runtime detection and configuration."""

import os
import shutil
from pathlib import Path
from typing import Dict, Optional

from mcp_runtime_server.types import Runtime, PackageManager, RuntimeConfig
from mcp_runtime_server.environments.runtime_binaries import ensure_binary
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


RUNTIME_CONFIGS: Dict[Runtime, RuntimeConfig] = {
    Runtime.NODE: RuntimeConfig(
        config_files=["package.json"],
        package_manager=PackageManager.NPM,
        env_setup={
            "NODE_NO_WARNINGS": "1",
            "NPM_CONFIG_UPDATE_NOTIFIER": "false"
        },
        bin_paths=["node_modules/.bin"],
        binary_name="node",
        url_template="https://nodejs.org/dist/{version_prefix}{version}/node-{version_prefix}{version}-{platform}-{arch}.{format}",
        checksum_template="https://nodejs.org/dist/{version_prefix}{version}/SHASUMS256.txt"
    ),
    Runtime.BUN: RuntimeConfig(
        config_files=["bun.lockb", "package.json"],
        package_manager=PackageManager.BUN,
        env_setup={"NO_INSTALL_HINTS": "1"},
        bin_paths=["node_modules/.bin"],
        binary_name="bun",
        url_template="https://github.com/oven-sh/bun/releases/download/bun-{version_prefix}{version}/bun-{platform}-{arch}.{format}",
        checksum_template="https://github.com/oven-sh/bun/releases/download/bun-{version_prefix}{version}/SHASUMS.txt",
        github_release=True
    ),
    Runtime.PYTHON: RuntimeConfig(
        config_files=["pyproject.toml", "setup.py", "requirements.txt"],
        package_manager=PackageManager.UV,
        env_setup={
            "PIP_NO_CACHE_DIR": "1",
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1"
        },
        bin_paths=[".venv/bin", ".venv/Scripts"],  # Scripts for Windows
        binary_name="uv",
        url_template="https://github.com/{owner}/{repo}/releases/download/{version_prefix}{version}/uv-{platform}.{format}",
        checksum_template=None,
        platform_style="composite",
        version_prefix="",
        github_release=True,
        owner="astral-sh",
        repo="uv"
    )
}


def detect_runtime(work_dir: Path) -> Runtime:
    """Detect runtime from project files.
    
    Args:
        work_dir: Working directory containing project files
        
    Returns:
        Detected runtime type
        
    Raises:
        ValueError: If no supported runtime is detected
    """
    logger.debug({
        "event": "detecting_runtime",
        "work_dir": str(work_dir)
    })
    
    # Get all files in the directory
    files = set(str(p) for p in work_dir.rglob("*"))
    logger.debug({
        "event": "found_project_files",
        "files": list(files)
    })

    # Check each runtime's config files
    for runtime, config in RUNTIME_CONFIGS.items():
        # For runtimes that need all config files
        if runtime == Runtime.BUN:
            if all(any(f.endswith(c) for f in files) for c in config.config_files):
                logger.info({
                    "event": "runtime_detected",
                    "runtime": runtime.value,
                    "matched_files": config.config_files
                })
                return runtime
        # For runtimes that need any config file
        else:
            if any(any(f.endswith(c) for f in files) for c in config.config_files):
                matched_file = next(
                    c for c in config.config_files 
                    if any(f.endswith(c) for f in files)
                )
                logger.info({
                    "event": "runtime_detected", 
                    "runtime": runtime.value,
                    "matched_file": matched_file,
                    "files_checked": config.config_files
                })
                return runtime

    logger.error({
        "event": "no_runtime_detected",
        "work_dir": str(work_dir),
        "files_found": list(files)
    })
    raise ValueError("No supported runtime detected")


def find_binary(name: str, paths: list[str], env_path: Optional[str] = None) -> Optional[Path]:
    """Find a binary in the given paths.
    
    Args:
        name: Binary name to find
        paths: List of paths to search
        env_path: Optional PATH environment variable
        
    Returns:
        Path to binary if found, None otherwise
    """
    # Check system PATH first if provided
    if env_path:
        system_bin = shutil.which(name, path=env_path)
        if system_bin:
            return Path(system_bin)

    # Check provided paths
    for path in paths:
        bin_path = Path(path) / name
        if not bin_path.exists() and os.name == "nt":
            bin_path = Path(path) / f"{name}.exe"
        if bin_path.exists():
            return bin_path

    return None


def get_runtime_bin_dir(work_dir: Path, runtime: Runtime) -> Path:
    """Get binary directory for a runtime.
    
    Args:
        work_dir: Working directory path
        runtime: Runtime type
        
    Returns:
        Path to binary directory
    """
    config = RUNTIME_CONFIGS[runtime]
    
    # Try each possible binary path
    for bin_path in config.bin_paths:
        full_path = work_dir / bin_path
        if full_path.exists():
            return full_path
            
    # Default to first path if none exist yet
    return work_dir / config.bin_paths[0]


async def prepare_runtime(runtime: Runtime, work_dir: Path, base_env: Dict[str, str]) -> Dict[str, str]:
    """Prepare runtime environment with binaries and environment variables.
    
    Args:
        runtime: Runtime to prepare
        work_dir: Working directory
        base_env: Base environment variables
        
    Returns:
        Dict of environment variables
        
    Raises:
        RuntimeError: If runtime preparation fails
    """
    config = RUNTIME_CONFIGS[runtime]
    
    # Ensure runtime binary is available
    try:
        binary_path = await ensure_binary(runtime, config)
        logger.info({
            "event": "runtime_binary_ready",
            "runtime": runtime.value,
            "binary_path": str(binary_path)
        })
    except Exception as e:
        logger.error({
            "event": "runtime_binary_failed",
            "runtime": runtime.value,
            "error": str(e)
        })
        raise RuntimeError(f"Failed to prepare {runtime.value} runtime: {e}")

    # Create environment
    env = base_env.copy()
    
    # Add runtime-specific base vars
    env.update(config.env_setup)

    # Add runtime-specific path vars
    bin_dir = get_runtime_bin_dir(work_dir, runtime)
    env["PATH"] = os.pathsep.join([str(bin_dir), binary_path.parent, env.get("PATH", "")])

    if runtime == Runtime.PYTHON:
        venv = work_dir / ".venv"
        env.update({
            "VIRTUAL_ENV": str(venv),
            "PYTHONPATH": str(work_dir)
        })
        logger.debug({
            "event": "python_env_setup",
            "venv_path": str(venv),
            "pythonpath": str(work_dir)
        })
    elif runtime in (Runtime.NODE, Runtime.BUN):
        modules_path = work_dir / "node_modules"
        env["NODE_PATH"] = str(modules_path)
        logger.debug({
            "event": "node_env_setup",
            "node_path": str(modules_path)
        })

    logger.info({
        "event": "runtime_prepared",
        "runtime": runtime.value,
        "work_dir": str(work_dir),
        "env_vars": {k: v for k, v in env.items() if k in config.env_setup or 
                    k in ["VIRTUAL_ENV", "PYTHONPATH", "NODE_PATH", "PATH"]}
    })

    return env
