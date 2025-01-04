"""Runtime binary management."""

from pathlib import Path
from typing import Optional
from mcp_runtime_server.utils.fs import copy_binary_to_dest
from mcp_runtime_server.types import Runtime, RuntimeConfig
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)

async def ensure_binary(binary_name: str, dest_dir: Path) -> Path:
    """Copy system binary to destination."""
    return await copy_binary_to_dest(binary_name, dest_dir)


