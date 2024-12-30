"""Unified release version management for runtime binaries."""
import re
import aiohttp
from typing import Optional
from mcp_runtime_server.binaries.constants import (
    GITHUB_API_BASE,
    GITHUB_REPOS_PATH,
    RELEASES_PATH,
    LATEST_PATH,
    UV_OWNER,
    UV_REPO
)


async def get_github_latest_release(
    owner: str = UV_OWNER, 
    repo: str = UV_REPO
) -> str:
    """Generic GitHub latest release fetcher."""
    url = f"{GITHUB_API_BASE}/{GITHUB_REPOS_PATH}/{owner}/{repo}/{RELEASES_PATH}/{LATEST_PATH}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            return data["tag_name"].lstrip("v")


async def get_nodejs_latest_release() -> str:
    """Fetch the latest Node.js release version."""
    async with aiohttp.ClientSession() as session:
        async with session.get("https://nodejs.org/dist/index.json") as response:
            response.raise_for_status()
            releases = await response.json()
            return releases[0]["version"].lstrip("v")


async def get_bun_latest_release() -> str:
    """Fetch the latest Bun release version."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://github.com/oven-sh/bun/releases/latest", 
            allow_redirects=True
        ) as response:
            response.raise_for_status()
            match = re.search(r"/tag/bun-v([\d.]+)", str(response.url))
            if not match:
                raise ValueError("Could not parse Bun release version")
            return match.group(1)
