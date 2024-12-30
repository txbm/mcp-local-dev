"""Release version management for runtime binaries."""
import aiohttp
from typing import Dict, Any

async def get_latest_uv_release() -> str:
    """Get the latest UV release version.
    
    Returns:
        Latest release version string (e.g. '1.0.0')
        
    Raises:
        RuntimeError: If unable to fetch release info
    """
    async with aiohttp.ClientSession() as session:
        url = "https://api.github.com/repos/astral-sh/uv/releases/latest"
        async with session.get(url) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Failed to fetch latest UV release: {response.status}"
                )
            data = await response.json()
            return data["tag_name"]
