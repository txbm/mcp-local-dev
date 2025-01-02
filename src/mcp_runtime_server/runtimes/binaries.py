"""Runtime binary management and downloads."""

import os
import re
import aiohttp
import zipfile
import tarfile
import tempfile
from pathlib import Path
from typing import List, Union

from mcp_runtime_server.types import Runtime, RuntimeConfig
from mcp_runtime_server.environments.platforms import (
    get_platform_info,
    get_binary_location,
)
from mcp_runtime_server.environments.cache import (
    get_binary_path,
    cache_binary,
    cleanup_cache,
)
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)

# GitHub API constants
GITHUB_API_BASE = "https://api.github.com"
GITHUB_REPOS_PATH = "repos"
RELEASES_PATH = "releases"
LATEST_PATH = "latest"


async def get_binary_release_version(runtime: Runtime, config: RuntimeConfig) -> str:
    """Get the latest version for a runtime binary."""
    async with aiohttp.ClientSession() as session:
        if not config.github_release:
            if runtime == Runtime.NODE:
                async with session.get(
                    "https://nodejs.org/dist/index.json"
                ) as response:
                    response.raise_for_status()
                    releases = await response.json()
                    return releases[0]["version"].lstrip("v")
            elif runtime == Runtime.BUN:
                async with session.get(
                    "https://github.com/oven-sh/bun/releases/latest",
                    allow_redirects=True,
                ) as response:
                    response.raise_for_status()
                    match = re.search(r"/tag/bun-v([\d.]+)", str(response.url))
                    if not match:
                        raise ValueError("Could not parse Bun release version")
                    return match.group(1)
        else:
            # GitHub release
            url = f"{GITHUB_API_BASE}/{GITHUB_REPOS_PATH}/{config.owner}/{config.repo}/releases/latest"
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                return data["tag_name"].lstrip("v")


async def ensure_binary(runtime: Runtime, config: RuntimeConfig) -> Path:
    """Ensure runtime binary is available.

    Args:
        runtime: Runtime to ensure binary for
        config: Runtime configuration

    Returns:
        Path to the binary

    Raises:
        RuntimeError: If binary cannot be obtained
    """
    platform_info = get_platform_info()

    try:
        # Get latest version
        version = await get_binary_release_version(runtime, config)

        # Check cache first
        cached_path = get_binary_path(config.binary_name, version)
        if cached_path:
            logger.info(
                {
                    "event": "using_cached_binary",
                    "runtime": runtime.value,
                    "version": version,
                    "path": str(cached_path),
                }
            )
            return cached_path

        # Format download URL
        url_vars = {
            "version": version,
            "version_prefix": config.version_prefix,
            "platform": (
                platform_info.node_platform
                if runtime == Runtime.NODE
                else (
                    platform_info.bun_platform
                    if runtime == Runtime.BUN
                    else platform_info.uv_platform
                )
            ),
            "format": platform_info.format,
            "arch": platform_info.arch,
        }

        if config.github_release:
            url_vars.update({"owner": config.owner, "repo": config.repo})

        download_url = config.url_template.format(**url_vars)

        # Format checksum URL if available
        checksum_url = None
        if config.checksum_template:
            checksum_url = config.checksum_template.format(**url_vars)

        # Download and extract
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            archive_path = tmp_path / Path(download_url).name

            logger.debug(
                {
                    "event": "downloading_binary",
                    "runtime": runtime.value,
                    "url": download_url,
                    "destination": str(archive_path),
                }
            )

            await download_binary(download_url, archive_path)

            # Verify checksum if available
            if checksum_url:
                if not await verify_checksum(
                    archive_path, checksum_url, config.binary_name
                ):
                    raise RuntimeError("Binary checksum verification failed")

            binary_location = get_binary_location(config.binary_name)
            print(binary_location)
            binary = extract_binary(archive_path, binary_location, tmp_path)

            # Cache the binary
            cached_binary = cache_binary(config.binary_name, version, binary, "")
            cleanup_cache()

            logger.info(
                {
                    "event": "binary_ready",
                    "runtime": runtime.value,
                    "version": version,
                    "path": str(cached_binary),
                }
            )

            return cached_binary

    except Exception as e:
        logger.error(
            {"event": "ensure_binary_failed", "runtime": runtime.value, "error": str(e)}
        )
        raise RuntimeError(f"Failed to ensure {runtime.value} binary: {e}")

    # Architecture mappings


ARCH_MAPPINGS = {
    "x86_64": {"node": "x64", "bun": "x64", "uv": "x86_64"},
    "aarch64": {"node": "arm64", "bun": "aarch64", "uv": "aarch64"},
    "arm64": {"node": "arm64", "bun": "aarch64", "uv": "aarch64"},
}

# Platform mappings with composite configuration
PLATFORM_MAPPINGS = {
    "Linux": PlatformMapping(
        node="linux",
        bun="linux",
        uv="unknown-linux-gnu",
        archive_format="tar.gz",
        platform_template="{arch}-{platform}",  # For UV-style composites
        binary_location="bin",  # No extension for Unix binaries
    ),
    "Darwin": PlatformMapping(
        node="darwin",
        bun="darwin",
        uv="apple-darwin",
        archive_format="tar.gz",
        platform_template="{arch}-{platform}",
        binary_location="bin",
    ),
    "Windows": PlatformMapping(
        node="win",
        bun="windows",
        uv="pc-windows-msvc",
        archive_format="zip",
        platform_template="{arch}-{platform}",
        binary_location="bin/{name}.exe",  # Windows executables need .exe
    ),
}


def get_platform_info() -> PlatformInfo:
    """Get current platform information."""
    system = platform.system()
    machine = platform.machine().lower()

    if system not in PLATFORM_MAPPINGS:
        raise RuntimeError(f"Unsupported operating system: {system}")

    # Handle ARM64 naming variations
    if machine in ("arm64", "aarch64"):
        machine = "aarch64"

    if machine not in ARCH_MAPPINGS:
        raise RuntimeError(f"Unsupported architecture: {machine}")

    platform_map = PLATFORM_MAPPINGS[system]
    arch_map = ARCH_MAPPINGS[machine]

    # Now we can compose platform strings based on the template
    uv_platform = platform_map.platform_template.format(
        arch=arch_map["uv"], platform=platform_map.uv
    )

    return PlatformInfo(
        os_name=system.lower(),
        arch=machine,
        format=platform_map.archive_format,
        node_platform=f"{platform_map.node}-{arch_map['node']}",
        bun_platform=f"{platform_map.bun}-{arch_map['bun']}",
        uv_platform=uv_platform,
    )


def get_binary_location(runtime_name: str, system: Optional[str] = None) -> str:
    """Get the appropriate binary path pattern for a runtime."""
    if system is None:
        system = platform.system()

    if system not in PLATFORM_MAPPINGS:
        raise RuntimeError(f"Unsupported operating system: {system}")

    platform_map = PLATFORM_MAPPINGS[system]
    return platform_map.binary_location.format(name=runtime_name)


def is_platform_supported() -> bool:
    """Check if current platform is supported."""
    try:
        get_platform_info()
        return True
    except RuntimeError:
        return False
