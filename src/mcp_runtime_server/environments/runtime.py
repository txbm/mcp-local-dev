"""Runtime configuration and management."""

import os
import re
import shutil
import hashlib
import platform
import aiohttp
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from mcp_runtime_server.types import Runtime, PackageManager, RuntimeConfig
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


def get_platform_info() -> Tuple[str, str, str]:
    """Get platform-specific information for binary downloads."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "darwin":
        system = "macos"
    
    if machine == "x86_64":
        machine = "x64"
    elif machine == "aarch64":
        machine = "arm64"
    elif machine.startswith("arm"):
        machine = "arm64"  # Assuming ARM is 64-bit
        
    if system == "windows":
        ext = "zip"
    else:
        ext = "tar.gz"
        
    return system, machine, ext


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


def verify_checksum(file_path: Path, expected: str) -> bool:
    """Verify file checksum."""
    sha256_hash = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
            
    return sha256_hash.hexdigest() == expected


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
    system, arch, format = get_platform_info()
    
    try:
        # Get latest version
        version = await get_binary_release_version(runtime)
        
        # Format download URL
        url_vars = {
            "version": version,
            "version_prefix": config.version_prefix,
            "platform": system,
            "arch": arch,
            "format": format
        }
        
        if config.github_release:
            url_vars.update({
                "owner": config.owner,
                "repo": config.repo
            })
            
        download_url = config.url_template.format(**url_vars)
        
        # Create temporary directory for download
        download_dir = Path("/tmp/mcp-downloads").resolve()
        download_dir.mkdir(exist_ok=True)
        
        # Download binary
        dest = download_dir / f"{config.binary_name}-{version}"
        if not dest.exists():
            await download_binary(download_url, dest)
            dest.chmod(0o755)
            
        return dest
        
    except Exception as e:
        logger.error({
            "event": "binary_fetch_failed",
            "runtime": runtime.value,
            "error": str(e)
        })
        raise RuntimeError(f"Failed to fetch {runtime.value} binary: {e}")
