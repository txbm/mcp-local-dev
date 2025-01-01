"""Runtime detection and configuration."""
import shutil
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from mcp_runtime_server.types import Runtime, Runtimes, RuntimeSignature
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


SIGNATURES = {
    Runtimes.NODE: RuntimeSignature(
        config_files=["package.json"],
        env_vars={
            "NODE_NO_WARNINGS": "1",
            "NPM_CONFIG_UPDATE_NOTIFIER": "false"
        },
        bin_path="node_modules/.bin"
    ),
    Runtimes.BUN: RuntimeSignature(
        config_files=["bun.lockb", "package.json"],
        env_vars={"NO_INSTALL_HINTS": "1"},
        bin_path="node_modules/.bin"
    ),
    Runtimes.PYTHON: RuntimeSignature(
        config_files=["pyproject.toml", "setup.py"],
        env_vars={
            "VIRTUAL_ENV": "",
            "PIP_NO_CACHE_DIR": "1"
        },
        bin_path=".venv/bin"
    )
}

def detect_runtime(work_dir: Path) -> Runtimes:
    """Detect runtime from project files."""
    try:
        files = set(str(p) for p in work_dir.rglob("*"))
        
        # Check Bun first (requires both files)
        if all(any(f.endswith(c) for f in files) 
              for c in SIGNATURES[Runtimes.BUN].config_files):
            return Runtimes.BUN
            
        # Then Node
        if any(f.endswith("package.json") for f in files):
            return Runtimes.NODE
            
        # Finally Python
        if any(any(f.endswith(c) for f in files) 
              for c in SIGNATURES[Runtimes.PYTHON].config_files):
            return Runtimes.PYTHON
            
        raise ValueError("No supported runtime detected")
        
    except Exception as e:
        raise RuntimeError(f"Runtime detection failed: {e}")

def get_runtime_binary(runtime: Runtimes) -> str:
    """Get runtime binary path."""
    binary = shutil.which(runtime.value)
    if not binary:
        raise RuntimeError(f"Runtime {runtime.value} not found")
    return binary

def get_runtime_bin_dir(work_dir: Path, runtime: Runtimes) -> Path:
    """Get runtime binary directory."""
    bin_path = work_dir / SIGNATURES[runtime].bin_path
    platform_bin = bin_path / "Scripts" if os.name == "nt" else bin_path
    return platform_bin if platform_bin.exists() else bin_path

def setup_runtime_env(
    base_env: Dict[str, str],
    runtime: Runtimes,
    work_dir: Path
) -> Dict[str, str]:
    """Setup runtime environment variables."""
    env = base_env.copy()
    bin_dir = get_runtime_bin_dir(work_dir, runtime)
    
    # Base PATH setup
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    
    # Runtime-specific vars
    runtime_vars = SIGNATURES[runtime].env_vars
    if runtime == Runtimes.PYTHON:
        venv = work_dir / ".venv"
        runtime_vars["VIRTUAL_ENV"] = str(venv)
        runtime_vars["PYTHONPATH"] = str(work_dir)
    elif runtime in (Runtimes.NODE, Runtimes.BUN):
        runtime_vars["NODE_PATH"] = str(work_dir / "node_modules")
        
    env.update(runtime_vars)
    return env
