"""Runtime configuration and management."""

import os
import re
import shutil
import aiohttp
import tempfile
import zipfile
import tarfile
from pathlib import Path
from typing import Dict, List, Optional, Union

from mcp_runtime_server.types import Runtime, PackageManager, RuntimeConfig
from mcp_runtime_server.environments.platforms import get_platform_info, get_binary_location
from mcp_runtime_server.environments.cache import (
    get_binary_path,
    cache_binary,
    cleanup_cache
)
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


RUNTIME_CONFIGS: Dict[Runtime, RuntimeConfig] = {
    Runtime.NODE: RuntimeConfig(
        config_files=["package.json"],
        package_manager=PackageManager.NPM,
        env_setup={
            "NODE_NO_WARNINGS": "1",
            "NPM_CONFIG_UPDATE_NOTIFIER": "false"
        },
        bin_paths=["node_modules/.bin"],
        binary_name="node",
        url_template="https://nodejs.org/dist/{version_prefix}{version}/node-{version_prefix}{version}-{platform}-{arch}.{format}",
        checksum_template="https://nodejs.org/dist/{version_prefix}{version}/SHASUMS256.txt"
    ),
    Runtime.BUN: RuntimeConfig(
        config_files=["bun.lockb", "package.json"],
        package_manager=PackageManager.BUN,
        env_setup={"NO_INSTALL_HINTS": "1"},
        bin_paths=["node_modules/.bin"],
        binary_name="bun",
        url_template="https://github.com/oven-sh/bun/releases/download/bun-{version_prefix}{version}/bun-{platform}-{arch}.{format}",
        checksum_template="https://github.com/oven-sh/bun/releases/download/bun-{version_prefix}{version}/SHASUMS.txt",
        github_release=True
    ),
    Runtime.PYTHON: RuntimeConfig(
        config_files=["pyproject.toml", "setup.py", "requirements.txt"],
        package_manager=PackageManager.UV,
        env_setup={
            "PIP_NO_CACHE_DIR": "1",
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1"
        },
        bin_paths=[".venv/bin", ".venv/Scripts"],  # Scripts for Windows
        binary_name="uv",
        url_template="https://github.com/{owner}/{repo}/releases/download/{version_prefix}{version}/uv-{platform}.{format}",
        checksum_template=None,
        platform_style="composite",
        version_prefix="",
        github_release=True,
        owner="astral-sh",
        repo="uv"
    )
}


def detect_runtime(work_dir: Path) -> Runtime:
    """Detect runtime from project files.
    
    Args:
        work_dir: Working directory containing project files
        
    Returns:
        Detected runtime type
        
    Raises:
        ValueError: If no supported runtime is detected
    """
    logger.debug({
        "event": "detecting_runtime",
        "work_dir": str(work_dir)
    })
    
    # Get all files in the directory
    files = set(str(p) for p in work_dir.rglob("*"))
    logger.debug({
        "event": "found_project_files",
        "files": list(files)
    })

    # Check each runtime's config files
    for runtime, config in RUNTIME_CONFIGS.items():
        # For runtimes that need all config files
        if runtime == Runtime.BUN:
            if all(any(f.endswith(c) for f in files) for c in config.config_files):
                logger.info({
                    "event": "runtime_detected",
                    "runtime": runtime.value,
                    "matched_files": config.config_files
                })
                return runtime
        # For runtimes that need any config file
        else:
            if any(any(f.endswith(c) for f in files) for c in config.config_files):
                matched_file = next(
                    c for c in config.config_files 
                    if any(f.endswith(c) for f in files)
                )
                logger.info({
                    "event": "runtime_detected", 
                    "runtime": runtime.value,
                    "matched_file": matched_file,
                    "files_checked": config.config_files
                })
                return runtime

    logger.error({
        "event": "no_runtime_detected",
        "work_dir": str(work_dir),
        "files_found": list(files)
    })
    raise ValueError("No supported runtime detected")


def find_binary(name: str, paths: List[str], env_path: Optional[str] = None) -> Optional[Path]:
    """Find a binary in the given paths.
    
    Args:
        name: Binary name to find
        paths: List of paths to search
        env_path: Optional PATH environment variable
        
    Returns:
        Path to binary if found, None otherwise
    """
    # Check system PATH first if provided
    if env_path:
        system_bin = shutil.which(name, path=env_path)
        if system_bin:
            return Path(system_bin)

    # Check provided paths
    for path in paths:
        bin_path = Path(path) / name
        if not bin_path.exists() and os.name == "nt":
            bin_path = Path(path) / f"{name}.exe"
        if bin_path.exists():
            return bin_path

    return None


def make_runtime_env(runtime: Runtime, sandbox_work_dir: Path, base_env: Dict[str, str]) -> Dict[str, str]:
    """Create runtime environment variables.
    
    Args:
        runtime: Runtime type to configure
        sandbox_work_dir: Sandbox working directory
        base_env: Base environment variables
        
    Returns:
        Dict of environment variables
    """
    logger.debug({
        "event": "creating_runtime_env",
        "runtime": runtime.value,
        "sandbox_work_dir": str(sandbox_work_dir)
    })

    env = base_env.copy()
    config = RUNTIME_CONFIGS[runtime]

    # Add runtime-specific base vars
    env.update(config.env_setup)

    # Add runtime-specific path vars
    if runtime == Runtime.PYTHON:
        venv = sandbox_work_dir / ".venv"
        env.update({
            "VIRTUAL_ENV": str(venv),
            "PYTHONPATH": str(sandbox_work_dir)
        })
        logger.debug({
            "event": "python_env_vars_added",
            "venv_path": str(venv),
            "pythonpath": str(sandbox_work_dir)
        })
    elif runtime in (Runtime.NODE, Runtime.BUN):
        modules_path = sandbox_work_dir / "node_modules"
        env["NODE_PATH"] = str(modules_path)
        logger.debug({
            "event": "node_env_vars_added",
            "node_path": str(modules_path)
        })

    logger.debug({
        "event": "runtime_env_created",
        "runtime": runtime.value,
        "runtime_specific_vars": {k: v for k, v in env.items() if k in config.env_setup or k in ["VIRTUAL_ENV", "PYTHONPATH", "NODE_PATH"]}
    })

    return env


async def get_binary_release_version(runtime: Runtime) -> str:
    """Get the latest version for a runtime binary."""
    config = RUNTIME_CONFIGS[runtime]
    
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
            url = f"https://api.github.com/repos/{config.owner}/{config.repo}/releases/latest"
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                return data["tag_name"].lstrip("v")


async def download_binary(url: str, dest: Path) -> None:
    """Download a binary file."""
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


async def ensure_runtime_binary(runtime: Runtime) -> Path:
    """Ensure runtime binary is available.
    
    Args:
        runtime: Runtime to ensure binary for
        
    Returns:
        Path to the binary
        
    Raises:
        RuntimeError: If binary cannot be obtained
    """
    config = RUNTIME_CONFIGS[runtime]
    platform_info = get_platform_info()
    
    try:
        # Get latest version
        version = await get_binary_release_version(runtime)
        
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
