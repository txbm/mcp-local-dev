"""Test configuration and fixtures."""
import os
import pytest
import tempfile
from pathlib import Path

from mcp_runtime_server.types import EnvironmentConfig  
from mcp_runtime_server.environments import create_environment, cleanup_environment

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def test_get_manager_binary(mocker):
    """Mock runtime binary discovery."""
    mocker.patch('shutil.which', side_effect=lambda x: f"/usr/bin/{x}")
    yield