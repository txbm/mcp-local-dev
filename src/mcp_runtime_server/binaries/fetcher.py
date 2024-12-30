"""Unified binary fetching and verification."""
import asyncio
import aiohttp
import tempfile
import zipfile
import tarfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union, Callable, List
from functools import partial

from mcp_runtime_server.binaries.constants import RUNTIME_BINARIES
from mcp_runtime_server.binaries.platforms import get_platform_info
from mcp_runtime_server.binaries.cache import (
    get_binary_path,
    cache_binary,
    cleanup_cache
)
from mcp_runtime_server.binaries.binary_info import get_binary_download_info

logger = logging.getLogger(__name__)

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

def get_archive_files(archive, ext: str) -> List[str]:
    """Get list of files from archive handling different archive types."""
    if ext == '.zip':
        return archive.namelist()
    else:  # tar-based archives
        return archive.getnames()

def extract_binary(
    archive_path: Path, 
    binary_path: str, 
    dest_dir: Path
) -> Path:
    """Extract binary from archive with flexible support."""
    extractors = {
        '.zip': (zipfile.ZipFile, get_archive_files),
        '.tar.gz': (tarfile.open, get_archive_files),
        '.tgz': (tarfile.open, get_archive_files)
    }
    
    ext = ''.join(archive_path.suffixes[-2:]) if len(archive_path.suffixes) > 1 else archive_path.suffix
    
    extractor_class, list_func = extractors.get(ext, (None, None))
    if not extractor_class:
        raise ValueError(f"Unsupported archive type: {ext}")

    with extractor_class(archive_path) as archive:
        binary_name = Path(binary_path).name
        matching_files = [
            f for f in list_func(archive, ext)
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
    download_url, version, binary_path = await get_binary_download_info(name, version)
    
    # Check cache
    cached = get_binary_path(name, version)
    if cached:
        return cached

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        archive_name = Path(download_url).name
        archive_path = tmp_path / archive_name
        
        # Download
        await download_file(download_url, archive_path)
        
        # Extract
        binary = extract_binary(archive_path, binary_path, tmp_path)
        
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