"""Runtime manager utilities."""
from typing import List, Dict, Tuple
import shutil
import os
from pathlib import Path

from mcp_runtime_server.types import RuntimeManager
from mcp_runtime_server.logging import logger
from mcp_runtime_server.errors import RuntimeServerError


def get_manager_binary(manager: RuntimeManager) -> str:
    """Get the path to the runtime manager binary.
    
    Args:
        manager: Runtime manager type
        
    Returns:
        Path to binary or command name
        
    Raises:
        RuntimeServerError: If manager binary not found
    """
    # Check if command exists in PATH
    binary = shutil.which(manager.value)
    if not binary:
        raise RuntimeServerError(f"Runtime manager {manager.value} not found in PATH")
    return binary


def build_install_command(
    manager: RuntimeManager,
    package: str,
    version: str = None,
    args: List[str] = None
) -> Tuple[str, List[str]]:
    """Build package installation command for a runtime manager.
    
    Args:
        manager: Runtime manager type
        package: Package name to install
        version: Optional version specification
        args: Additional arguments
        
    Returns:
        Tuple of (command, arguments list)
        
    Raises:
        RuntimeServerError: If manager is not supported
    """
    if args is None:
        args = []
        
    if manager == RuntimeManager.NPX:
        # NPX command format
        cmd = get_manager_binary(manager)
        pkg_spec = f"{package}@{version}" if version else package
        return cmd, ["-y", "--no-install-links", pkg_spec, *args]
        
    elif manager == RuntimeManager.BUNX:
        # Bun command format
        cmd = get_manager_binary(manager)
        pkg_spec = f"{package}@{version}" if version else package
        return cmd, [pkg_spec, *args]
        
    elif manager == RuntimeManager.UVX:
        # UV command format
        cmd = get_manager_binary(manager)
        if version:
            return cmd, ["--version", version, package, *args]
        return cmd, [package, *args]
        
    elif manager == RuntimeManager.PIPX:
        # PIPX command format
        cmd = get_manager_binary(manager)
        if version:
            pkg_spec = f"{package}=={version}"
        else:
            pkg_spec = package
        return cmd, ["run", "--no-cache", pkg_spec, *args]
        
    else:
        raise RuntimeServerError(f"Unsupported runtime manager: {manager}")


def validate_package_name(manager: RuntimeManager, package: str) -> bool:
    """Validate package name format for a runtime manager.
    
    Args:
        manager: Runtime manager type
        package: Package name to validate
        
    Returns:
        True if package name is valid
    """
    if not package:
        return False
        
    # Basic validation - could be enhanced for each manager
    if manager in (RuntimeManager.NPX, RuntimeManager.BUNX):
        # NPM package naming rules
        return all(c.isalnum() or c in "-_@/" for c in package)
        
    elif manager == RuntimeManager.UVX:
        # Python package naming rules
        return all(c.isalnum() or c in "-_." for c in package)
        
    elif manager == RuntimeManager.PIPX:
        # Python package naming rules
        return all(c.isalnum() or c in "-_." for c in package)
        
    return False


def prepare_env_vars(
    manager: RuntimeManager,
    base_env: Dict[str, str]
) -> Dict[str, str]:
    """Prepare environment variables for a runtime manager.
    
    Args:
        manager: Runtime manager type
        base_env: Base environment variables
        
    Returns:
        Dict of environment variables
    """
    env = base_env.copy()
    
    if manager == RuntimeManager.NPX:
        # NPX specific environment setup
        env.update({
            "NPX_NO_UPDATE_NOTIFIER": "1",
            "NO_UPDATE_NOTIFIER": "1",
            "NPM_CONFIG_UPDATE_NOTIFIER": "false"
        })
        
    elif manager == RuntimeManager.BUNX:
        # Bun specific environment setup
        env.update({
            "BUNX_CACHE": env.get("BUNX_CACHE", "/tmp/bunx-cache"),
            "NO_INSTALL_HINTS": "1"
        })
        
    elif manager == RuntimeManager.UVX:
        # UV specific environment setup
        env.update({
            "VIRTUAL_ENV": env.get("VIRTUAL_ENV", ""),
            "PIP_NO_CACHE_DIR": "1",
            "PIP_NO_WARN_SCRIPT_LOCATION": "1"
        })
        
    elif manager == RuntimeManager.PIPX:
        # PIPX specific environment setup
        env.update({
            "PIPX_HOME": env.get("PIPX_HOME", "/tmp/pipx"),
            "PIPX_BIN_DIR": env.get("PIPX_BIN_DIR", "/tmp/pipx/bin"),
            "PIP_NO_CACHE_DIR": "1"
        })
        
    return env


def cleanup_manager_artifacts(
    manager: RuntimeManager,
    working_dir: str
) -> None:
    """Clean up artifacts left by a runtime manager.
    
    Args:
        manager: Runtime manager type
        working_dir: Working directory to clean
    """
    work_path = Path(working_dir)
    
    if manager == RuntimeManager.NPX:
        # Clean NPX/NPM artifacts
        for pattern in ["node_modules", "package*.json", ".npm"]:
            for path in work_path.glob(pattern):
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink(missing_ok=True)
                    
    elif manager == RuntimeManager.BUNX:
        # Clean Bun artifacts
        for pattern in ["node_modules", "bun.lockb", ".bun"]:
            for path in work_path.glob(pattern):
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink(missing_ok=True)
                    
    elif manager == RuntimeManager.UVX:
        # Clean UV artifacts
        for pattern in [".venv", "__pycache__", "*.pyc"]:
            for path in work_path.glob(pattern):
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink(missing_ok=True)
                    
    elif manager == RuntimeManager.PIPX:
        # Clean PIPX artifacts
        pipx_home = Path(os.environ.get("PIPX_HOME", "/tmp/pipx"))
        if pipx_home.exists():
            shutil.rmtree(pipx_home, ignore_errors=True)