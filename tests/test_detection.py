"""Tests for runtime detection."""
import os
import tempfile
from pathlib import Path

from mcp_runtime_server.types import RuntimeManager
from mcp_runtime_server.detection import detect_runtime


def test_node_detection():
    """Test Node.js project detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "package.json").touch()
        
        runtime = detect_runtime(tmpdir)
        assert runtime is not None
        assert runtime.manager == RuntimeManager.NODE


def test_bun_detection():
    """Test Bun project detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Should not detect as Bun with just package.json
        Path(tmpdir, "package.json").touch()
        runtime = detect_runtime(tmpdir)
        assert runtime is not None
        assert runtime.manager == RuntimeManager.NODE
        
        # Should detect as Bun with both files
        Path(tmpdir, "bun.lockb").touch()
        runtime = detect_runtime(tmpdir)
        assert runtime is not None
        assert runtime.manager == RuntimeManager.BUN


def test_python_detection():
    """Test Python project detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test pyproject.toml
        Path(tmpdir, "pyproject.toml").touch()
        runtime = detect_runtime(tmpdir)
        assert runtime is not None
        assert runtime.manager == RuntimeManager.UV
        
        # Test setup.py
        Path(tmpdir).mkdir(exist_ok=True)
        Path(tmpdir, "setup.py").touch()
        runtime = detect_runtime(tmpdir)
        assert runtime is not None
        assert runtime.manager == RuntimeManager.UV


def test_unknown_project():
    """Test unrecognized project detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime = detect_runtime(tmpdir)
        assert runtime is None


def test_nested_files():
    """Test detection with nested config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        nested = Path(tmpdir, "src", "project")
        nested.mkdir(parents=True)
        
        Path(nested, "package.json").touch()
        
        runtime = detect_runtime(tmpdir)
        assert runtime is not None
        assert runtime.manager == RuntimeManager.NODE
        
        # Add bun.lockb, should switch to Bun
        Path(nested, "bun.lockb").touch()
        runtime = detect_runtime(tmpdir)
        assert runtime is not None
        assert runtime.manager == RuntimeManager.BUN