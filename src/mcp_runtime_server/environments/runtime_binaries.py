"""Runtime binary management and downloads."""

import os
import re
import aiohttp
import zipfile
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union

from mcp_runtime_server.types import Runtime, RuntimeConfig
from mcp_runtime_server.environments.platforms import get_platform_info, get_binary_location
from mcp_runtime_server.environments.cache import (
    get_binary_path,
    cache_binary,
    cleanup_cache
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
                async with session.get("https://nodejs.org/dist/index.json") as response:
                    response.raise_for_status()
                    releases = await response.json()
                    return releases[0]["version"].lstrip("v")
            elif runtime == Runtime.BUN:
                async with session.get(
                    "https://github.com/oven-sh/bun/releases/latest",
                    allow_redirects=True
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


async def download_binary(url: str, dest: Path) -> None:
    """Download a binary file with checksum verification."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise RuntimeError(f"Download failed with status {response.status}")
                
                with open(dest, "wb") as f:
                    while chunk := await response.content.read(8192):
                        f.write(chunk)
                        
    except Exception as e:
        if dest.exists():
            dest.unlink()
        raise RuntimeError(f"Failed to download binary: {e}")


async def verify_checksum(file_path: Path, checksum_url: str, binary_name: str) -> bool:
    """Verify the checksum of a downloaded binary."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(checksum_url) as response:
                response.raise_for_status()
                checksums = await response.text()
                
                # Find the checksum for our binary
                for line in checksums.splitlines():
                    if binary_name in line:
                        expected_checksum, _ = line.split()
                        import hashlib
                        with open(file_path, "rb") as f:
                            actual_checksum = hashlib.sha256(f.read()).hexdigest()
                            return actual_checksum == expected_checksum
                            
        return False
    except Exception as e:
        logger.error({
            "event": "checksum_verification_failed",
            "error": str(e),
            "file": str(file_path),
            "checksum_url": checksum_url
        })
        return False


def get_archive_files(archive: Union[zipfile.ZipFile, tarfile.TarFile], format: str) -> List[str]:
    """Get list of files from archive handling different archive types."""
    try:
        if isinstance(archive, zipfile.ZipFile):
            return archive.namelist()
        else:  # tarfile.TarFile
            return archive.getnames()
    except Exception as e:
        logger.error({
            "event": "list_archive_failed",
            "format": format,
            "error": str(e)
        })
        raise ValueError(f"Failed to read {format} archive") from e


def extract_binary(archive_path: Path, binary_path: str, dest_dir: Path) -> Path:
    """Extract binary from archive with flexible support."""
    format = "".join(archive_path.suffixes[-2:]) if len(archive_path.suffixes) > 1 else archive_path.suffix
    
    archive_handlers = {
        ".zip": zipfile.ZipFile,
        ".tar.gz": tarfile.open,
        ".tgz": tarfile.open
    }
    
    handler = archive_handlers.get(format)
    if not handler:
        raise ValueError(f"Unsupported archive format: {format}")

    try:
        with handler(archive_path) as archive:
            binary_name = Path(binary_path).name
            all_files = get_archive_files(archive, format)
            
            matching_files = [f for f in all_files if f.endswith(binary_name)]
            if not matching_files:
                logger.error({
                    "event": "binary_not_found",
                    "archive": str(archive_path),
                    "binary_name": binary_name,
                    "available_files": all_files
                })
                raise ValueError(f"Binary {binary_name} not found in archive")

            target = matching_files[0]
            archive.extract(target, dest_dir)
            extracted_path = Path(dest_dir) / target
            
            if not extracted_path.exists():
                logger.error({
                    "event": "extracted_file_missing",
                    "archive": str(archive_path),
                    "expected_path": str(extracted_path)
                })
                raise ValueError("Failed to extract binary - file missing after extraction")
            
            # Set executable permissions on Unix-like systems
            if os.name != "nt":
                extracted_path.chmod(0o755)
            
            logger.info({
                "event": "binary_extracted",
                "archive": str(archive_path),
                "binary": binary_name,
                "extracted_to": str(extracted_path)
            })
            
            return extracted_path
            
    except Exception as e:
        if not isinstance(e, ValueError):  # Don't wrap our own exceptions
            logger.error({
                "event": "extract_failed",
                "archive": str(archive_path),
                "format": format,
                "error": str(e)
            })
            raise ValueError(f"Failed to extract from {archive_path.name}") from e
        raise


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
            logger.info({
                "event": "using_cached_binary",
                "runtime": runtime.value,
                "version": version,
                "path": str(cached_path)
            })
            return cached_path

        # Format download URL
        url_vars = {
            "version": version,
            "version_prefix": config.version_prefix,
            "platform": platform_info.node_platform if runtime == Runtime.NODE else
                       platform_info.bun_platform if runtime == Runtime.BUN else
                       platform_info.uv_platform,
            "format": platform_info.format,
            "arch": platform_info.arch
        }
        
        if config.github_release:
            url_vars.update({
                "owner": config.owner,
                "repo": config.repo
            })
            
        download_url = config.url_template.format(**url_vars)
        
        # Format checksum URL if available
        checksum_url = None
        if config.checksum_template:
            checksum_url = config.checksum_template.format(**url_vars)
        
        # Download and extract
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            archive_path = tmp_path / Path(download_url).name
            
            logger.debug({
                "event": "downloading_binary",
                "runtime": runtime.value,
                "url": download_url,
                "destination": str(archive_path)
            })
            
            await download_binary(download_url, archive_path)
            
            # Verify checksum if available
            if checksum_url:
                if not await verify_checksum(archive_path, checksum_url, config.binary_name):
                    raise RuntimeError("Binary checksum verification failed")
            
            binary_location = get_binary_location(config.binary_name)
            binary = extract_binary(archive_path, binary_location, tmp_path)
            
            # Cache the binary
            cached_binary = cache_binary(config.binary_name, version, binary, "")
            cleanup_cache()
            
            logger.info({
                "event": "binary_ready",
                "runtime": runtime.value,
                "version": version,
                "path": str(cached_binary)
            })
            
            return cached_binary
        
    except Exception as e:
        logger.error({
            "event": "ensure_binary_failed",
            "runtime": runtime.value,
            "error": str(e)
        })
        raise RuntimeError(f"Failed to ensure {runtime.value} binary: {e}")
