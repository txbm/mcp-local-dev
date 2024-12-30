"""Binary fetching and verification."""
import asyncio
import aiohttp
import tempfile
import zipfile
import tarfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from mcp_runtime_server.binaries.constants import RUNTIME_BINARIES
from mcp_runtime_server.binaries.platforms import get_platform_info
from mcp_runtime_server.binaries.releases import get_latest_uv_release
from mcp_runtime_server.binaries.cache import (
    get_binary_path,
    cache_binary,
    cleanup_cache,
    verify_checksum
)

logger = logging.getLogger(__name__)


async def download_file(url: str, dest: Path) -> None:
    """Download a file."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise RuntimeError(f"Failed to download {url}: {response.status}")
            
            with open(dest, 'wb') as f:
                while True:
                    chunk = await response.content.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)


async def get_uv_release_urls(base_api_url: str, version: str, platform_str: str) -> Tuple[str, str, str]:
    """Get UV release binary and checksum URLs."""
    release_url = f"{base_api_url}/releases/tags/{version}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(release_url) as response:
            if response.status != 200:
                raise RuntimeError(f"Failed to fetch UV release info: {response.status}")
            release = await response.json()
            
            # Find binary and checksum assets
            binary_name = f"uv-{platform_str}.tar.gz"
            binary_url = None
            checksum_url = None
            
            for asset in release["assets"]:
                if asset["name"] == binary_name:
                    binary_url = asset["browser_download_url"]
                elif asset["name"] == "sha256.sum":
                    checksum_url = asset["browser_download_url"]
                    
            if not binary_url or not checksum_url:
                raise RuntimeError(f"Failed to find UV release assets for {platform_str}")
                
            return binary_url, checksum_url


async def verify_uv_binary(binary_path: Path, checksum_url: str, binary_name: str) -> None:
    """Verify UV binary checksum."""
    async with aiohttp.ClientSession() as session:
        async with session.get(checksum_url) as response:
            if response.status != 200:
                raise RuntimeError(f"Failed to fetch checksums: {response.status}")
                
            content = await response.text()
            
            for line in content.splitlines():
                try:
                    checksum, name = line.strip().split(maxsplit=1)
                    if name == binary_name:
                        if not verify_checksum(binary_path, checksum):
                            raise RuntimeError("Binary checksum verification failed")
                        return
                except ValueError:
                    continue
                    
            raise RuntimeError(f"Checksum not found for {binary_name}")


def extract_binary(archive_path: Path, binary_path: str, dest_dir: Path) -> Path:
    """Extract binary from archive."""
    if archive_path.suffix == '.zip':
        with zipfile.ZipFile(archive_path) as zf:
            binary_name = Path(binary_path).name
            binary_files = [f for f in zf.namelist() if f.endswith(binary_name)]
            
            if not binary_files:
                raise RuntimeError(f"Binary {binary_name} not found in archive")
                
            zf.extract(binary_files[0], dest_dir)
            return dest_dir / binary_files[0]
            
    else:  # Assume tar.gz
        with tarfile.open(archive_path) as tf:
            binary_name = Path(binary_path).name
            binary_files = [f for f in tf.getnames() if f.endswith(binary_name)]
            
            if not binary_files:
                raise RuntimeError(f"Binary {binary_name} not found in archive")
                
            tf.extract(binary_files[0], dest_dir)
            return dest_dir / binary_files[0]


async def fetch_binary(name: str) -> Path:
    """Fetch a binary."""
    if name == "uv":
        return await fetch_uv_binary()
    
    spec = RUNTIME_BINARIES[name]
    version = spec["version"]
    
    cached = get_binary_path(name, version)
    if cached:
        return cached
    
    platform_info = get_platform_info()
    platform_map = {
        "node": platform_info.node_platform,
        "bun": platform_info.bun_platform
    }
    
    platform_str = platform_map[name]
    download_url = spec["url_template"].format(
        version=version,
        platform=platform_str.split("-")[0],
        arch=platform_str.split("-")[1]
    )
    checksum_url = spec["checksum_template"].format(version=f"v{version}")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        archive_name = Path(download_url).name
        archive_path = tmp_path / archive_name
        
        await download_file(download_url, archive_path)
        
        binary = extract_binary(archive_path, spec["binary_path"], tmp_path)
        cached_path = cache_binary(name, version, binary, "")
        cleanup_cache()
        
        return cached_path


async def fetch_uv_binary() -> Path:
    """Fetch UV binary using GitHub API."""
    spec = RUNTIME_BINARIES["uv"]
    version = await get_latest_uv_release()
    
    cached = get_binary_path("uv", version)
    if cached:
        return cached
    
    platform_info = get_platform_info()
    binary_url, checksum_url = await get_uv_release_urls(
        spec["api_url"], 
        version,
        platform_info.uv_platform
    )
    
    binary_name = Path(binary_url).name
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        archive_path = tmp_path / binary_name
        
        await download_file(binary_url, archive_path)
        await verify_uv_binary(archive_path, checksum_url, binary_name)
        
        binary = extract_binary(archive_path, spec["binary_path"], tmp_path)
        cached_path = cache_binary("uv", version, binary, "")
        cleanup_cache()
        
        return cached_path


async def ensure_binary(name: str) -> Path:
    """Ensure a binary is available."""
    try:
        return await fetch_binary(name)
    except Exception as e:
        raise RuntimeError(f"Failed to ensure binary {name}: {e}") from e
