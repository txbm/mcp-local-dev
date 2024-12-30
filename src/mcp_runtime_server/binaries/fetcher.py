"""Unified binary fetching and verification."""
import asyncio
import aiohttp
import tempfile
import zipfile
import tarfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union, Callable
from functools import partial

from mcp_runtime_server.binaries.constants import RUNTIME_BINARIES
from mcp_runtime_server.binaries.platforms import get_platform_info
from mcp_runtime_server.binaries.cache import (
    get_binary_path,
    cache_binary,
    cleanup_cache
)
from mcp_runtime_server.binaries.releases import (
    get_github_latest_release,
    get_nodejs_latest_release,
    get_bun_latest_release
)

logger = logging.getLogger(__name__)

RELEASE_STRATEGIES = {
    "uv": get_github_latest_release,
    "node": get_nodejs_latest_release,
    "bun": get_bun_latest_release
}

def with_error_handling(func):
    """Decorator for consistent error handling in binary fetching."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"{func.__name__} failed: {e}")
            raise RuntimeError(f"Binary fetch failed: {e}") from e
    return wrapper

async def download_file(
    url: str, 
    dest: Path, 
    headers: Optional[Dict[str, str]] = None
) -> None:
    """Download a file with streaming."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()
            with open(dest, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)

def extract_binary(
    archive_path: Path, 
    binary_path: str, 
    dest_dir: Path
) -> Path:
    """Extract binary from archive with flexible support."""
    extractors = {
        '.zip': zipfile.ZipFile,
        '.tar.gz': tarfile.open,
        '.tgz': tarfile.open
    }
    
    ext = ''.join(archive_path.suffixes[-2:]) if len(archive_path.suffixes) > 1 else archive_path.suffix
    
    extractor = extractors.get(ext)
    if not extractor:
        raise ValueError(f"Unsupported archive type: {ext}")

    with extractor(archive_path) as archive:
        binary_name = Path(binary_path).name
        matching_files = [
            f for f in archive.namelist() 
            if f.endswith(binary_name)
        ]

        if not matching_files:
            raise RuntimeError(f"Binary {binary_name} not found in archive")

        archive.extract(matching_files[0], dest_dir)
        return Path(dest_dir) / matching_files[0]

@with_error_handling
async def fetch_binary(
    name: str, 
    version: Optional[str] = None
) -> Path:
    """Fetch a binary with unified strategy."""
    spec = RUNTIME_BINARIES[name]
    
    # Determine version
    if version is None:
        release_strategy = RELEASE_STRATEGIES.get(name)
        if release_strategy:
            version = await release_strategy()
        else:
            version = spec.get("version")
    
    # Check cache
    cached = get_binary_path(name, version)
    if cached:
        return cached

    # Platform detection
    platform_info = get_platform_info()
    platform_map = {
        "node": platform_info.node_platform,
        "bun": platform_info.bun_platform,
        "uv": platform_info.uv_platform
    }
    platform_str = platform_map[name]
    platform, arch = platform_str.split("-")

    # URL construction
    download_url = spec["url_template"].format(
        version=version,
        platform=platform,
        arch=arch
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        archive_name = Path(download_url).name
        archive_path = tmp_path / archive_name
        
        # Download
        await download_file(download_url, archive_path)
        
        # Extract
        binary = extract_binary(archive_path, spec["binary_path"], tmp_path)
        
        # Cache
        cached_path = cache_binary(name, version, binary, "")
        cleanup_cache()
        
        return cached_path

def create_binary_fetcher(name: str):
    """Create a specialized fetcher for a specific runtime."""
    return partial(fetch_binary, name)

# Pre-configured fetchers for convenience
node_fetcher = create_binary_fetcher("node")
bun_fetcher = create_binary_fetcher("bun")
uv_fetcher = create_binary_fetcher("uv")

async def ensure_binary(name: str) -> Path:
    """Ensure a binary is available."""
    try:
        return await fetch_binary(name)
    except Exception as e:
        logger.error(f"Binary fetch failed for {name}: {e}")
        raise RuntimeError(f"Failed to ensure binary {name}") from e
