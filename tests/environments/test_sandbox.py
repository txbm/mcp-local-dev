"""Tests for sandbox creation and security."""
import os
import stat
import tempfile
from pathlib import Path

from mcp_runtime_server.environments.sandbox import (
    create_sandbox,
    cleanup_sandbox,
    _create_directories,
    _prepare_environment,
    _apply_security
)

def test_sandbox_with_tempdir():
    """Test sandbox creation within TemporaryDirectory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        info = create_sandbox(root)
        try:
            # Check core directories exist
            assert info.root.exists()
            assert info.work_dir.exists()
            assert info.bin_dir.exists()
            
            # Verify within tempdir
            assert info.root == root
            assert info.work_dir.is_relative_to(root)
            assert info.bin_dir.is_relative_to(root)
            
        finally:
            cleanup_sandbox(info.root)
        
        # Temp directory should still exist
        assert root.exists()
        
    # Now temp directory should be gone
    assert not root.exists()

def test_sandbox_env_vars():
    """Test sandbox environment variable preparation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        info = create_sandbox(Path(tmpdir))
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

def test_sandbox_cleanup_layers():
    """Test layered sandbox cleanup behavior."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        info = create_sandbox(root)
        
        # Create test content
        test_dir = info.work_dir / "testdir"
        test_dir.mkdir()
        test_file = test_dir / "test.txt"
        test_file.touch()
        
        # Test sandbox cleanup
        cleanup_sandbox(info.root)
        assert not test_file.exists()
        assert not test_dir.exists()
        assert not info.work_dir.exists()
        
        # Temp directory should still exist but be empty
        assert root.exists()
        assert not any(root.iterdir())
        
    # Temp directory should be gone
    assert not root.exists()

def test_sandbox_security():
    """Test sandbox security restrictions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        info = create_sandbox(Path(tmpdir))
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
                # Check restrictive permissions
                assert work_file.stat().st_mode & 0o777 == 0o600
                
        finally:
            cleanup_sandbox(info.root)

def test_sandbox_cleanup_idempotency():
    """Test that cleanup is idempotent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        info = create_sandbox(root)
        
        # First cleanup
        cleanup_sandbox(info.root)
        assert not info.work_dir.exists()
        
        # Second cleanup should not error
        cleanup_sandbox(info.root)
        
        # Root should still exist for TemporaryDirectory
        assert root.exists()