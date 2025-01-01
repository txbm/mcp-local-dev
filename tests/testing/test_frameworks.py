"""Tests for test framework detection and execution."""

import os
import pytest
from pathlib import Path
from typing import List, Set
from unittest.mock import Mock, patch, AsyncMock

from mcp_runtime_server.types import Environment
from mcp_runtime_server.testing.frameworks import (
    TestFramework,
    detect_frameworks,
    run_pytest,
    run_unittest,
    run_framework_tests,
    _has_test_files,
    _check_file_imports,
    _find_test_dirs
)


def test_has_test_files(tmp_path: Path):
    """Test detection of test files in a directory."""
    # Create test files
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    
    (test_dir / "test_one.py").write_text("# Test file")
    (test_dir / "test_two.py").write_text("# Another test")
    (test_dir / "not_a_test.py").write_text("# Not a test")
    
    assert _has_test_files(test_dir, '.py')
    assert not _has_test_files(test_dir, '.java')
    assert not _has_test_files(tmp_path / "nonexistent", '.py')


def test_check_file_imports(tmp_path: Path):
    """Test detection of imports in Python files."""
    test_file = tmp_path / "test_imports.py"
    
    # Test pytest import
    test_file.write_text("import pytest\nfrom pytest import fixture")
    assert _check_file_imports(test_file, ['pytest'])
    
    # Test unittest import
    test_file.write_text("import unittest\nfrom unittest import TestCase")
    assert _check_file_imports(test_file, ['unittest'])
    
    # Test no matching imports
    test_file.write_text("import other\nfrom other import thing")
    assert not _check_file_imports(test_file, ['pytest', 'unittest'])
    
    # Test nonexistent file
    assert not _check_file_imports(tmp_path / "nonexistent.py", ['pytest'])


def test_find_test_dirs(tmp_path: Path):
    """Test finding test directories in a project."""
    # Create test directory structure
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/unit").mkdir()
    (tmp_path / "tests/integration").mkdir()
    (tmp_path / "src/module/tests").mkdir(parents=True)
    
    # Create test files
    (tmp_path / "tests/test_main.py").write_text("# Test file")
    (tmp_path / "tests/unit/test_utils.py").write_text("# Unit test")
    (tmp_path / "src/module/tests/test_module.py").write_text("# Module test")
    
    test_dirs = _find_test_dirs(tmp_path)
    test_dir_names = {p.name for p in test_dirs}
    
    assert "tests" in test_dir_names
    assert "unit" in test_dir_names
    assert len(test_dirs) >= 3


def test_detect_frameworks_pytest(tmp_path: Path):
    """Test detection of pytest framework."""
    # Create test files and structure
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    
    # Add pytest indicators
    (tests_dir / "conftest.py").write_text("# Pytest config")
    (tests_dir / "test_pytest.py").write_text("import pytest\ndef test_something(): pass")
    
    frameworks = detect_frameworks(str(tmp_path))
    assert TestFramework.PYTEST in frameworks


def test_detect_frameworks_unittest(tmp_path: Path):
    """Test detection of unittest framework."""
    # Create test files and structure
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    
    # Add unittest file
    unittest_content = """
import unittest
class TestSomething(unittest.TestCase):
    def test_method(self):
        pass
"""
    (tests_dir / "test_unittest.py").write_text(unittest_content)
    
    frameworks = detect_frameworks(str(tmp_path))
    assert TestFramework.UNITTEST in frameworks


def test_detect_frameworks_multiple(tmp_path: Path):
    """Test detection of multiple test frameworks."""
    # Create test files and structure
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    
    # Add both pytest and unittest files
    (tests_dir / "conftest.py").write_text("# Pytest config")
    (tests_dir / "test_pytest.py").write_text("import pytest\ndef test_something(): pass")
    
    unittest_content = """
import unittest
class TestSomething(unittest.TestCase):
    def test_method(self):
        pass
"""
    (tests_dir / "test_unittest.py").write_text(unittest_content)
    
    frameworks = detect_frameworks(str(tmp_path))
    assert TestFramework.PYTEST in frameworks
    assert TestFramework.UNITTEST in frameworks


@pytest.mark.asyncio
async def test_run_pytest():
    """Test running pytest tests."""
    env = Mock(spec=Environment)
    env.bin_dir = Mock(spec=Path)
    env.work_dir = Mock(spec=Path)
    env.env_vars = {}
    
    # Mock pytest executable
    pytest_path = env.bin_dir / "pytest"
    pytest_path.exists.return_value = True
    
    # Mock subprocess
    process_mock = AsyncMock()
    process_mock.returncode = 0
    process_mock.communicate.return_value = (b"", b'{"summary": {"passed": 1}}')
    
    with patch('mcp_runtime_server.testing.frameworks.run_command', 
               return_value=process_mock):
        result = await run_pytest(env)
    
    assert result["success"]
    assert result["framework"] == TestFramework.PYTEST


@pytest.mark.asyncio
async def test_run_unittest():
    """Test running unittest tests."""
    env = Mock(spec=Environment)
    env.bin_dir = Mock(spec=Path)
    env.work_dir = Mock(spec=Path)
    env.env_vars = {}
    
    # Mock python executable
    python_path = env.bin_dir / "python"
    python_path.exists.return_value = True
    
    # Mock subprocess
    process_mock = AsyncMock()
    process_mock.returncode = 0
    process_mock.communicate.return_value = (b"OK\n", b"")
    
    with patch('mcp_runtime_server.testing.frameworks.run_command',
               return_value=process_mock):
        result = await run_unittest(env)
    
    assert result["success"]
    assert result["framework"] == TestFramework.UNITTEST


@pytest.mark.asyncio
async def test_run_framework_tests():
    """Test running tests for different frameworks."""
    env = Mock(spec=Environment)
    env.bin_dir = Mock(spec=Path)
    env.work_dir = Mock(spec=Path)
    env.env_vars = {}
    
    # Mock executables
    pytest_path = env.bin_dir / "pytest"
    pytest_path.exists.return_value = True
    
    python_path = env.bin_dir / "python"
    python_path.exists.return_value = True
    
    # Mock subprocess
    process_mock = AsyncMock()
    process_mock.returncode = 0
    process_mock.communicate.return_value = (b"", b'{"summary": {"passed": 1}}')
    
    with patch('mcp_runtime_server.testing.frameworks.run_command',
               return_value=process_mock):
        # Test pytest
        result = await run_framework_tests(TestFramework.PYTEST, env)
        assert result["success"]
        assert result["framework"] == TestFramework.PYTEST
        
        # Test unittest
        process_mock.communicate.return_value = (b"OK\n", b"")
        result = await run_framework_tests(TestFramework.UNITTEST, env)
        assert result["success"]
        assert result["framework"] == TestFramework.UNITTEST
        
        # Test unsupported framework
        with pytest.raises(ValueError, match="Unsupported framework"):
            await run_framework_tests("invalid", env)