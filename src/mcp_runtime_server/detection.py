"""Runtime detection utilities."""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from mcp_runtime_server.types import RuntimeManager


@dataclass(frozen=True)
class RuntimeSignature:
    """Runtime detection signature."""
    manager: RuntimeManager
    config_files: List[str]
    env_vars: Dict[str, str]


SIGNATURES = {
    RuntimeManager.NPX: RuntimeSignature(
        manager=RuntimeManager.NPX,
        config_files=["package.json", "package-lock.json", "yarn.lock"],
        env_vars={
            "NPX_NO_UPDATE_NOTIFIER": "1",
            "NO_UPDATE_NOTIFIER": "1",
            "NPM_CONFIG_UPDATE_NOTIFIER": "false"
        }
    ),
    RuntimeManager.BUN: RuntimeSignature(
        manager=RuntimeManager.BUN,
        config_files=["bun.lockb", "package.json"],
        env_vars={
            "BUNX_CACHE": "/tmp/bunx-cache",
            "NO_INSTALL_HINTS": "1"
        }
    ),
    RuntimeManager.UVX: RuntimeSignature(
        manager=RuntimeManager.UVX,
        config_files=["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt"],
        env_vars={
            "VIRTUAL_ENV": "",
            "PIP_NO_CACHE_DIR": "1",
            "PIP_NO_WARN_SCRIPT_LOCATION": "1"
        }
    ),
    RuntimeManager.PIPX: RuntimeSignature(
        manager=RuntimeManager.PIPX,
        config_files=["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt"],
        env_vars={
            "PIPX_HOME": "/tmp/pipx",
            "PIPX_BIN_DIR": "/tmp/pipx/bin",
            "PIP_NO_CACHE_DIR": "1"
        }
    )
}


def detect_runtime(project_dir: str) -> Optional[RuntimeSignature]:
    """Detect runtime based on project files.
    
    Args:
        project_dir: Project directory to examine
        
    Returns:
        Detected runtime signature or None
    """
    try:
        path = Path(project_dir)
        all_files = set(str(p) for p in path.rglob("*"))

        # BUN gets priority over NPX for JS projects
        for manager in [RuntimeManager.BUN, RuntimeManager.NPX, RuntimeManager.UVX, RuntimeManager.PIPX]:
            sig = SIGNATURES[manager]
            if any(any(f.endswith(c) for f in all_files) for c in sig.config_files):
                return sig
                    
        return None
        
    except Exception as e:
        raise RuntimeError(f"Failed to detect runtime: {e}")
