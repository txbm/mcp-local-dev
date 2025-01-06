"""Runtime detection and configuration."""

from typing import Dict, Callable, Awaitable
from mcp_local_dev.types import Runtime, RuntimeConfig, Sandbox
from mcp_local_dev.logging import get_logger
from mcp_local_dev.runtimes import python, node, bun

logger = get_logger(__name__)

# Map of runtime configs
RUNTIME_CONFIGS: Dict[Runtime, RuntimeConfig] = {
    Runtime.PYTHON: python.CONFIG,
    Runtime.NODE: node.CONFIG,
    Runtime.BUN: bun.CONFIG,
}

# Map of runtime setup functions
RUNTIME_SETUP: Dict[Runtime, Callable[[Sandbox], Awaitable[None]]] = {
    Runtime.PYTHON: python.setup_python,
    Runtime.NODE: node.setup_node,
    Runtime.BUN: bun.setup_bun,
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

async def install_runtime(sandbox: Sandbox, config: RuntimeConfig) -> None:
    """Install runtime by setting up package manager and installing dependencies"""
    setup_func = RUNTIME_SETUP.get(config.name)
    if not setup_func:
        raise RuntimeError(f"No setup function for runtime: {config.name}")
        
    await setup_func(sandbox)
