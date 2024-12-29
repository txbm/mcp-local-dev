"""Binary and artifact caching."""
import os
import json
import hashlib
import shutil
from pathlib import Path
from typing import Dict, Optional, Set
import appdirs


def get_cache_dir() -> Path:
    """Get the cache directory for binaries and artifacts.
    
    Returns:
        Path to cache directory
    """
    cache_dir = Path(appdirs.user_cache_dir("mcp-runtime-server"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_state_file() -> Path:
    """Get the path to the state file.
    
    Returns:
        Path to state file
    """
    return get_cache_dir() / "state.json"


def load_state() -> Dict:
    """Load cache state from disk.
    
    Returns:
        Dict containing cache state
    """
    state_file = get_state_file()
    if state_file.exists():
        try:
            with open(state_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"binaries": {}, "checksums": {}}
    return {"binaries": {}, "checksums": {}}


def save_state(state: Dict) -> None:
    """Save cache state to disk.
    
    Args:
        state: Cache state to save
    """
    state_file = get_state_file()
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)


def get_binary_path(name: str, version: str) -> Optional[Path]:
    """Get path to a cached binary.
    
    Args:
        name: Binary name
        version: Binary version
        
    Returns:
        Path to binary if cached, None otherwise
    """
    state = load_state()
    binary_info = state["binaries"].get(f"{name}-{version}")
    
    if binary_info:
        path = Path(binary_info["path"])
        if path.exists():
            return path
    return None


def cache_binary(
    name: str,
    version: str,
    binary_path: Path,
    checksum: str
) -> Path:
    """Cache a binary.
    
    Args:
        name: Binary name
        version: Binary version
        binary_path: Path to binary
        checksum: Binary checksum
        
    Returns:
        Path to cached binary
        
    Raises:
        ValueError: If binary checksum doesn't match
    """
    if not verify_checksum(binary_path, checksum):
        raise ValueError(f"Checksum mismatch for {name} {version}")
    
    # Cache location
    cache_dir = get_cache_dir() / "bin" / f"{name}-{version}"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy binary to cache
    cached_path = cache_dir / binary_path.name
    shutil.copy2(binary_path, cached_path)
    
    # Make binary executable
    cached_path.chmod(0o755)
    
    # Update state
    state = load_state()
    state["binaries"][f"{name}-{version}"] = {
        "path": str(cached_path),
        "checksum": checksum,
        "cached_at": str(Path(cached_path).stat().st_mtime)
    }
    save_state(state)
    
    return cached_path


def verify_checksum(path: Path, expected: str) -> bool:
    """Verify a file's checksum.
    
    Args:
        path: Path to file
        expected: Expected checksum
        
    Returns:
        True if checksum matches
    """
    sha256 = hashlib.sha256()
    
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
            
    return sha256.hexdigest() == expected


def cleanup_cache(
    max_versions: int = 2,
    max_size_mb: int = 1024
) -> None:
    """Clean up old cached binaries.
    
    Args:
        max_versions: Maximum versions to keep per binary
        max_size_mb: Maximum cache size in MB
    """
    state = load_state()
    cache_dir = get_cache_dir()
    
    # Group by binary name
    by_name: Dict[str, Set[str]] = {}
    for key in state["binaries"]:
        name = key.split('-')[0]
        by_name.setdefault(name, set()).add(key)
        
    # Remove old versions
    for name, versions in by_name.items():
        if len(versions) > max_versions:
            sorted_versions = sorted(
                versions,
                key=lambda v: float(state["binaries"][v]["cached_at"]),
                reverse=True
            )
            
            for old_version in sorted_versions[max_versions:]:
                binary_info = state["binaries"][old_version]
                path = Path(binary_info["path"])
                if path.exists():
                    path.unlink()
                if path.parent.exists() and not any(path.parent.iterdir()):
                    path.parent.rmdir()
                del state["binaries"][old_version]
    
    # Check total size
    total_size = sum(
        path.stat().st_size
        for path in cache_dir.rglob('*')
        if path.is_file()
    )
    
    if total_size > max_size_mb * 1024 * 1024:
        # Remove oldest until under limit
        binaries = sorted(
            state["binaries"].items(),
            key=lambda x: float(x[1]["cached_at"])
        )
        
        for key, info in binaries:
            path = Path(info["path"])
            if path.exists():
                file_size = path.stat().st_size
                path.unlink()
                if path.parent.exists() and not any(path.parent.iterdir()):
                    path.parent.rmdir()
                del state["binaries"][key]
                total_size -= file_size
                
            if total_size <= max_size_mb * 1024 * 1024:
                break
                
    save_state(state)