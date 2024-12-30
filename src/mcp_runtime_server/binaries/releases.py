"""Release version management for runtime binaries."""
import aiohttp
from typing import Dict, Any
from mcp_runtime_server.binaries.constants import (
    UV_API_BASE,
    RELEASES_PATH,
    LATEST_PATH
)

async def get_latest_uv_release() -> str:
    """Get the latest UV release version.
    
    Returns:
        Latest release version string
        
    Raises:
        RuntimeError: If unable to fetch release info
    """
    url = f"{UV_API_BASE}/{RELEASES_PATH}/{LATEST_PATH}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Failed to fetch latest UV release: {response.status}"
                )
            data = await response.json()
            return data["tag_name"]
