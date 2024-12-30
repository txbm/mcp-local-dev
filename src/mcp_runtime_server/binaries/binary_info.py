"""Binary-specific information and handling."""

import re
import platform
import aiohttp
from typing import Any, Dict, Optional, Tuple, NamedTuple
from mcp_runtime_server.binaries.constants import (
    GITHUB_API_BASE,
    GITHUB_REPOS_PATH,
    RELEASES_PATH,
    LATEST_PATH,
    UV_OWNER,
    UV_REPO,
)
from mcp_runtime_server.binaries.platforms import (
    get_platform_info,
    get_binary_location,
    PLATFORM_MAPPINGS,
)


class RuntimeInfo(NamedTuple):
    """Binary runtime configuration."""

    url_template: str
    checksum_template: Optional[str]
    binary_name: str
    version_prefix: str = "v"  # How version numbers are prefixed in URLs
    github_release: bool = False  # Whether this is a GitHub release URL pattern
    platform_style: str = "simple"  # Use 'simple' or 'composite' platform strings


RUNTIME_CONFIGS = {
    "node": RuntimeInfo(
        url_template="https://nodejs.org/dist/{version_prefix}{version}/node-{version_prefix}{version}-{platform}-{arch}.{format}",
        checksum_template="https://nodejs.org/dist/{version_prefix}{version}/SHASUMS256.txt",
        binary_name="node",
        version_prefix="v",
    ),
    "bun": RuntimeInfo(
        url_template="https://github.com/oven-sh/bun/releases/download/bun-{version_prefix}{version}/bun-{platform}-{arch}.{format}",
        checksum_template="https://github.com/oven-sh/bun/releases/download/bun-{version_prefix}{version}/SHASUMS.txt",
        binary_name="bun",
        version_prefix="v",
        github_release=True,
    ),
    "uv": RuntimeInfo(
        url_template="https://github.com/{owner}/{repo}/releases/download/{version_prefix}{version}/uv-{platform}.{format}",
        checksum_template=None,
        binary_name="uv",
        version_prefix="",
        github_release=True,
        platform_style="composite",
    ),
}

RELEASE_STRATEGIES = {
    "uv": "get_github_latest_release",
    "node": "get_nodejs_latest_release",
    "bun": "get_bun_latest_release",
}


async def get_github_latest_release(owner: str = UV_OWNER, repo: str = UV_REPO) -> str:
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
            "https://github.com/oven-sh/bun/releases/latest", allow_redirects=True
        ) as response:
            response.raise_for_status()
            match = re.search(r"/tag/bun-v([\d.]+)", str(response.url))
            if not match:
                raise ValueError("Could not parse Bun release version")
            return match.group(1)


def format_url(
    template: str,
    runtime_name: str,
    version: str,
    platform_str: str,
    format: str,
    **kwargs,
) -> str:
    """Format URL with consistent handling of platform strings."""
    config = RUNTIME_CONFIGS[runtime_name]
    system = platform.system()

    # Get values needed for all URL patterns
    values = {
        "version": version,
        "version_prefix": config.version_prefix,
        "format": format,
        **kwargs,  # Allow additional values like owner/repo for GitHub URLs
    }

    # Handle platform string based on style
    if config.platform_style == "composite":
        values["platform"] = platform_str
    else:
        if "-" in platform_str:
            plat, arch = platform_str.split("-")
            values["platform"] = plat
            values["arch"] = arch
        else:
            values["platform"] = platform_str
            values["arch"] = "x64"

    return template.format(**values)


async def get_binary_download_info(
    name: str, version: Optional[str] = None
) -> Tuple[str, str, str]:
    """Get binary download information."""
    if name not in RUNTIME_CONFIGS:
        raise ValueError(f"Unknown runtime: {name}")

    config = RUNTIME_CONFIGS[name]

    # Determine version
    if version is None:
        release_strategy = RELEASE_STRATEGIES.get(name)
        if release_strategy:
            strategy_func = globals()[release_strategy]
            version = await strategy_func()
        else:
            raise ValueError(f"No release strategy for {name} and no version provided")

    # Get platform information
    platform_info = get_platform_info()
    platform_map = {
        "node": platform_info.node_platform,
        "bun": platform_info.bun_platform,
        "uv": platform_info.uv_platform,
    }
    platform_str = platform_map[name]

    # Format download URL
    extra_values = {}
    if config.github_release:
        if name == "uv":
            extra_values.update({"owner": UV_OWNER, "repo": UV_REPO})

    assert version

    download_url = format_url(
        config.url_template,
        name,
        version,
        platform_str,
        platform_info.format,
        **extra_values,
    )

    # Get binary path based on platform
    binary_path = f"{get_binary_location(config.binary_name)}/{config.binary_name}"

    return download_url, version, binary_path
