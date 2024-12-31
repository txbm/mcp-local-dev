"""Unified binary fetching and verification."""
import asyncio
import aiohttp
import tempfile
import zipfile
import tarfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union, Callable, List, Tuple
from functools import partial

from mcp_runtime_server.binaries.constants import RUNTIME_BINARIES
from mcp_runtime_server.binaries.platforms import get_platform_info
from mcp_runtime_server.binaries.cache import (
    get_binary_path,
    cache_binary,
    cleanup_cache
)
from mcp_runtime_server.binaries.binary_info import get_binary_download_info

logger = logging.getLogger("mcp_runtime_server.binaries.fetcher")

async def download_file(
    url: str, 
    dest: Path, 
    headers: Optional[Dict[str, str]] = None
) -> None:
    """Download a file with streaming."""
    try:
        async with aiohttp.ClientSession() as session:
            logger.info("Starting binary download", extra={
                'data': {
                    'url': url,
                    'destination': str(dest)
                }
            })
            
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.error("Download request failed", extra={
                        'data': {
                            'url': url,
                            'status': response.status,
                            'reason': response.reason,
                            'headers': dict(response.headers)
                        }
                    })
                    response.raise_for_status()
                
                size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(dest, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                logger.info("Binary download complete", extra={
                    'data': {
                        'url': url,
                        'size': downloaded,
                        'expected_size': size
                    }
                })
                
    except aiohttp.ClientError as e:
        logger.error("Binary download failed", extra={
            'data': {
                'url': url,
                'error': str(e),
                'status': getattr(e, 'status', None)
            }
        })
        raise ValueError(f"Failed to download from {url}") from e

def get_archive_files(archive: Union[zipfile.ZipFile, tarfile.TarFile], format: str) -> List[str]:
    """Get list of files from archive handling different archive types."""
    try:
        if isinstance(archive, zipfile.ZipFile):
            return archive.namelist()
        else:  # tarfile.TarFile
            return archive.getnames()
    except Exception as e:
        logger.error("Failed to list archive contents", extra={
            'data': {
                'format': format,
                'error': str(e)
            }
        })
        raise ValueError(f"Failed to read {format} archive") from e

def extract_binary(
    archive_path: Path, 
    binary_path: str, 
    dest_dir: Path
) -> Path:
    """Extract binary from archive with flexible support."""
    format = ''.join(archive_path.suffixes[-2:]) if len(archive_path.suffixes) > 1 else archive_path.suffix
    
    archive_handlers = {
        '.zip': zipfile.ZipFile,
        '.tar.gz': tarfile.open,
        '.tgz': tarfile.open
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
                logger.error("Binary not found in archive", extra={
                    'data': {
                        'archive': str(archive_path),
                        'binary_name': binary_name,
                        'available_files': all_files
                    }
                })
                raise ValueError(f"Binary {binary_name} not found in archive")

            target = matching_files[0]
            archive.extract(target, dest_dir)
            extracted_path = Path(dest_dir) / target
            
            if not extracted_path.exists():
                logger.error("Extracted file missing", extra={
                    'data': {
                        'archive': str(archive_path),
                        'expected_path': str(extracted_path)
                    }
                })
                raise ValueError("Failed to extract binary - file missing after extraction")
            
            logger.info("Binary extracted successfully", extra={
                'data': {
                    'archive': str(archive_path),
                    'binary': binary_name,
                    'extracted_to': str(extracted_path)
                }
            })
            
            return extracted_path
            
    except Exception as e:
        if not isinstance(e, ValueError):  # Don't wrap our own exceptions
            logger.error("Failed to extract binary", extra={
                'data': {
                    'archive': str(archive_path),
                    'format': format,
                    'error': str(e)
                }
            })
            raise ValueError(f"Failed to extract from {archive_path.name}") from e
        raise

async def fetch_binary(
    name: str, 
    version: Optional[str] = None
) -> Path:
    """Fetch a binary with unified strategy."""
    try:
        download_url, version, binary_path = await get_binary_download_info(name, version)
        
        logger.info("Fetching binary", extra={
            'data': {
                'name': name,
                'version': version,
                'url': download_url
            }
        })
        
        # Check cache first
        cached = get_binary_path(name, version)
        if cached:
            logger.info("Using cached binary", extra={
                'data': {
                    'name': name,
                    'version': version,
                    'path': str(cached)
                }
            })
            return cached

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            archive_path = tmp_path / Path(download_url).name
            
            # Download
            await download_file(download_url, archive_path)
            
            if not archive_path.exists() or archive_path.stat().st_size == 0:
                logger.error("Downloaded archive is missing or empty", extra={
                    'data': {
                        'path': str(archive_path),
                        'exists': archive_path.exists(),
                        'size': archive_path.stat().st_size if archive_path.exists() else 0
                    }
                })
                raise ValueError("Download failed - archive is missing or empty")
            
            # Extract
            binary = extract_binary(archive_path, binary_path, tmp_path)
            
            # Cache
            cached_path = cache_binary(name, version, binary, "")
            cleanup_cache()
            
            logger.info("Binary fetch complete", extra={
                'data': {
                    'name': name,
                    'version': version,
                    'path': str(cached_path)
                }
            })
            
            return cached_path
            
    except Exception as e:
        logger.error("Binary fetch failed", extra={
            'data': {
                'name': name,
                'version': version,
                'error': str(e)
            }
        })
        raise ValueError(f"Failed to fetch {name}") from e

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
        # No need to re-log here since fetch_binary already logs errors
        raise ValueError(f"Failed to ensure binary {name}") from None  # Suppress traceback