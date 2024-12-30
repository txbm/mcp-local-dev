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
    RuntimeManager.NODE: RuntimeSignature(
        manager=RuntimeManager.NODE,
        config_files=["package.json"],
        env_vars={
            "NODE_NO_WARNINGS": "1"
        }
    ),
    RuntimeManager.BUN: RuntimeSignature(
        manager=RuntimeManager.BUN,
        config_files=["bun.lockb", "package.json"],
        env_vars={
            "NO_INSTALL_HINTS": "1"
        }
    ),
    RuntimeManager.UV: RuntimeSignature(
        manager=RuntimeManager.UV,
        config_files=["pyproject.toml", "setup.py"],
        env_vars={
            "VIRTUAL_ENV": "",
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
        files = set(str(p) for p in path.rglob("*"))

        # First check for Bun since it requires both bun.lockb and package.json
        bun_sig = SIGNATURES[RuntimeManager.BUN]
        if all(any(f.endswith(c) for f in files) for c in bun_sig.config_files):
            return bun_sig

        # Then check Node (package.json)
        if any(f.endswith("package.json") for f in files):
            return SIGNATURES[RuntimeManager.NODE]

        # Finally check for Python
        if any(any(f.endswith(c) for f in files) for c in SIGNATURES[RuntimeManager.UV].config_files):
            return SIGNATURES[RuntimeManager.UV]

        return None

    except Exception as e:
        raise RuntimeError(f"Failed to detect runtime: {e}")