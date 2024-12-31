"""Sandbox creation and security."""
import os
import shutil
import stat
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)

@dataclass(frozen=True)
class SandboxInfo:
    root: Path
    work_dir: Path
    bin_dir: Path
    env_vars: Dict[str, str]

def create_sandbox(base_dir: Path, sandbox_id: str) -> SandboxInfo:
    """Create new sandbox environment."""
    sandbox_root = base_dir / f"sandbox-{sandbox_id}"
    try:
        dirs = _create_directories(sandbox_root)
        env_vars = _prepare_environment(sandbox_root, dirs)
        _apply_security(sandbox_root)
        
        return SandboxInfo(
            root=sandbox_root,
            work_dir=dirs["work"],
            bin_dir=dirs["bin"],
            env_vars=env_vars
        )
    except Exception as e:
        if sandbox_root.exists():
            shutil.rmtree(sandbox_root, ignore_errors=True)
        raise RuntimeError(f"Failed to create sandbox: {e}")

def _create_directories(root: Path) -> Dict[str, Path]:
    """Create sandbox directory structure."""
    dirs = {
        "bin": root / "bin",
        "tmp": root / "tmp", 
        "work": root / "work",
        "cache": root / "cache"
    }
    
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
        
    return dirs

def _prepare_environment(
    root: Path, 
    dirs: Dict[str, Path]
) -> Dict[str, str]:
    """Prepare sandbox environment variables."""
    env = os.environ.copy()
    
    env.update({
        "TMPDIR": str(dirs["tmp"]),
        "XDG_CACHE_HOME": str(dirs["cache"]),
        "XDG_RUNTIME_DIR": str(dirs["tmp"]),
        "PATH": f"{dirs['bin']}{os.pathsep}{env.get('PATH', '')}"
    })
    
    # Remove unsafe vars
    for var in ["LD_PRELOAD", "LD_LIBRARY_PATH"]:
        env.pop(var, None)
        
    return env

def _apply_security(root: Path) -> None:
    """Apply security restrictions."""
    if platform.system() == "Linux":
        _apply_unix_permissions(root)
        
def _apply_unix_permissions(path: Path) -> None:
    """Apply restrictive Unix permissions."""
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    
    if path.is_dir():
        for child in path.iterdir():
            _apply_unix_permissions(child)

def cleanup_sandbox(root: Path) -> None:
    """Clean up sandbox environment."""
    try:
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)
    except Exception as e:
        raise RuntimeError(f"Failed to clean up sandbox: {e}")