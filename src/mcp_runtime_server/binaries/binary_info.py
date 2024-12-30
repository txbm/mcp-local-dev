"""Binary-specific information and handling."""
import re
import aiohttp
from typing import Any, Dict, Optional, Tuple
from mcp_runtime_server.binaries.constants import (
    GITHUB_API_BASE,
    GITHUB_REPOS_PATH,
    RELEASES_PATH,
    LATEST_PATH,
    UV_OWNER,
    UV_REPO
)
from mcp_runtime_server.binaries.platforms import get_platform_info

RELEASE_STRATEGIES = {
    "uv": "get_github_latest_release",
    "node": "get_nodejs_latest_release",
    "bun": "get_bun_latest_release"
}

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

async def get_binary_download_info(name: str, version: Optional[str] = None) -> Tuple[str, str, str]:
    """Get binary download information."""
    spec = RUNTIME_BINARIES[name]
    
    # Determine version
    if version is None:
        release_strategy = RELEASE_STRATEGIES.get(name)
        if release_strategy:
            # Await the async release strategy function
            strategy_func = globals()[release_strategy]
            version = await strategy_func()
        else:
            version = spec.get("version")
    
    platform_info = get_platform_info()
    platform_map = {
        "node": platform_info.node_platform,
        "bun": platform_info.bun_platform,
        "uv": platform_info.uv_platform
    }
    platform_str = platform_map[name]
    
    if name == "uv":
        # Get extension based on the platform
        if any(platform in platform_str for platform in ["windows"]):
            extension = ".zip"
        else:
            extension = ".tar.gz"
            
        download_url = (
            f"https://github.com/{UV_OWNER}/{UV_REPO}/releases/download/"
            f"{version}/uv-{platform_str}{extension}"
        )
    else:
        # For other runtimes, split into platform and arch
        if "-" in platform_str:
            platform, arch = platform_str.split("-")
        else:
            platform = platform_str
            arch = "x64"  # Default to 64-bit architecture
            
        download_url = spec["url_template"].format(
            version=version,
            platform=platform,
            arch=arch
        )
    
    return download_url, version, spec["binary_path"]

RUNTIME_BINARIES: Dict[str, Any] = {
    "node": {
        "version": "20.10.0",
        "url_template": "https://nodejs.org/dist/v{version}/node-v{version}-{platform}-{arch}.tar.gz",
        "checksum_template": "https://nodejs.org/dist/v{version}/SHASUMS256.txt",
        "binary_path": "bin/node",
        "npx_path": "bin/npx"
    },
    "bun": {
        "version": "1.0.21",
        "url_template": "https://github.com/oven-sh/bun/releases/download/bun-v{version}/bun-{platform}-{arch}.zip",
        "checksum_template": "https://github.com/oven-sh/bun/releases/download/bun-v{version}/SHASUMS.txt",
        "binary_path": "bun"
    },
    "uv": {
        "version": None,  # Will be fetched dynamically
        "binary_path": "uv"
    }
}
