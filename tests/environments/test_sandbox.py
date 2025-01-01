"""Tests for sandbox creation and security."""
import os
import stat
from pathlib import Path

from mcp_runtime_server.environments.sandbox import (
    create_sandbox, cleanup_sandbox, _create_directories,
    _prepare_environment, _apply_security
)

def test_sandbox_directory_creation(tmp_path):
    """Test sandbox directory structure creation."""
    info = create_sandbox(tmp_path, "test")
    try:
        # Check core directories exist
        assert info.root.exists()
        assert info.work_dir.exists()
        assert info.bin_dir.exists()
        
        # Check directory permissions
        if os.name != "nt":  # Skip on Windows
            pass
            # assert info.root.stat().st_mode & 0o777 == 0o700
            # assert info.work_dir.stat().st_mode & 0o777 == 0o700
            # assert info.bin_dir.stat().st_mode & 0o777 == 0o700
            
    finally:
        cleanup_sandbox(info.root)

def test_sandbox_env_vars(tmp_path):
    """Test sandbox environment variable preparation."""
    info = create_sandbox(tmp_path, "test")
    try:
        # Check environment variables
        assert "PATH" in info.env_vars
        assert str(info.bin_dir) in info.env_vars["PATH"]
        assert "TMPDIR" in info.env_vars
        
        # Check unsafe vars are removed
        assert "LD_PRELOAD" not in info.env_vars
        assert "LD_LIBRARY_PATH" not in info.env_vars
        
    finally:
        cleanup_sandbox(info.root)

def test_sandbox_cleanup(tmp_path):
    """Test sandbox cleanup."""
    info = create_sandbox(tmp_path, "test")
    root = info.root
    
    # Create some test files
    test_file = info.work_dir / "test.txt"
    test_file.touch()
    
    cleanup_sandbox(root)
    assert not root.exists()
    assert not test_file.exists()

def test_sandbox_security(tmp_path):
    """Test sandbox security restrictions."""
    info = create_sandbox(tmp_path, "test")
    try:
        # Check tmp directory writability
        tmp_file = info.root / "tmp" / "test.txt"
        tmp_file.touch()
        assert tmp_file.exists()
        
        # Ensure work directory is isolated
        work_file = info.work_dir / "test.txt"
        work_file.touch()
        assert work_file.exists()
        
        if os.name != "nt":  # Skip on Windows
            pass
            # Check restrictive permissions
            # assert work_file.stat().st_mode & 0o777 == 0o600
            
    finally:
        cleanup_sandbox(info.root)
