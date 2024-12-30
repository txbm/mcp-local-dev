"""Binary cache management."""
import os
import shutil
import hashlib
import logging
from pathlib import Path
from typing import Optional
from mcp_runtime_server.logging import log_with_data

logger = logging.getLogger(__name__)

CACHE_DIR = Path(os.path.expanduser("~/.cache/mcp_runtime_server/binaries"))
MAX_CACHE_SIZE = 1024 * 1024 * 1024  # 1 GB

def compute_file_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        log_with_data(logger, logging.ERROR, "Failed to compute file hash", {
            'file': str(path),
            'error': str(e)
        })
        raise RuntimeError(f"Checksum failure for {path.name}") from e

def get_binary_path(name: str, version: str) -> Optional[Path]:
    """Get cached binary path if it exists."""
    cache_path = CACHE_DIR / name / version / "binary"
    hash_path = cache_path.with_suffix('.sha256')
    
    if not cache_path.exists() or not hash_path.exists():
        return None
        
    try:
        stored_hash = hash_path.read_text().strip()
        current_hash = compute_file_hash(cache_path)
        
        if stored_hash != current_hash:
            log_with_data(logger, logging.ERROR, "Cache validation failed", {
                'binary': name,
                'version': version,
                'stored_hash': stored_hash,
                'computed_hash': current_hash
            })
            return None
            
        return cache_path
    except Exception as e:
        log_with_data(logger, logging.ERROR, "Cache access error", {
            'binary': name,
            'version': version,
            'error': str(e)
        })
        return None

def cache_binary(name: str, version: str, binary_path: Path, checksum: str) -> Path:
    """Cache a binary file with version and checksum."""
    cache_path = CACHE_DIR / name / version
    cache_path.mkdir(parents=True, exist_ok=True)
    
    binary_cache = cache_path / "binary"
    hash_path = binary_cache.with_suffix('.sha256')
    
    try:
        # Copy binary to cache
        shutil.copy2(binary_path, binary_cache)
        binary_cache.chmod(0o755)  # Ensure binary is executable
        
        # Compute and store hash
        computed_hash = compute_file_hash(binary_cache)
        hash_path.write_text(computed_hash)
        
        # Verify checksum if provided
        if checksum and computed_hash != checksum:
            log_with_data(logger, logging.ERROR, "Checksum verification failed", {
                'binary': name,
                'version': version,
                'computed': computed_hash,
                'expected': checksum
            })
            raise RuntimeError(f"Checksum mismatch for {name} {version}")
            
        log_with_data(logger, logging.INFO, "Binary cached successfully", {
            'binary': name,
            'version': version,
            'path': str(binary_cache),
            'hash': computed_hash
        })
        
        return binary_cache
        
    except Exception as e:
        log_with_data(logger, logging.ERROR, "Failed to cache binary", {
            'binary': name,
            'version': version,
            'error': str(e)
        })
        raise RuntimeError(f"Failed to cache {name} {version}") from e

def cleanup_cache() -> None:
    """Remove old cache entries if total size exceeds limit."""
    if not CACHE_DIR.exists():
        return
        
    try:
        total_size = sum(f.stat().st_size for f in CACHE_DIR.rglob('*') if f.is_file())
        
        if total_size > MAX_CACHE_SIZE:
            # Get list of binaries sorted by modification time
            cache_files = sorted(
                [(f, f.stat().st_mtime) for f in CACHE_DIR.rglob('binary')],
                key=lambda x: x[1]
            )
            
            # Remove oldest files until under limit
            for cache_file, _ in cache_files:
                if total_size <= MAX_CACHE_SIZE:
                    break
                    
                file_size = cache_file.stat().st_size
                cache_file.unlink()
                cache_file.with_suffix('.sha256').unlink()
                total_size -= file_size
                
                log_with_data(logger, logging.INFO, "Removed cached binary", {
                    'path': str(cache_file),
                    'size': file_size
                })
                
    except Exception as e:
        log_with_data(logger, logging.ERROR, "Cache cleanup failed", {
            'error': str(e)
        })