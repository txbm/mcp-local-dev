"""Release version management for runtime binaries."""
import aiohttp
from typing import Dict, Any
from mcp_runtime_server.binaries.constants import RUNTIME_BINARIES

async def get_latest_uv_release() -> str:
    """Get the latest UV release version.
    
    Returns:
        Latest release version string
        
    Raises:
        RuntimeError: If unable to fetch release info
    """
    spec = RUNTIME_BINARIES["uv"]
    async with aiohttp.ClientSession() as session:
        url = f"{spec['api_url']}/releases/latest"
        async with session.get(url) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Failed to fetch latest UV release: {response.status}"
                )
            data = await response.json()
            return data["tag_name"]