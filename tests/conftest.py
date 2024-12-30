"""Test configuration and fixtures."""
import pytest
import tempfile
from pathlib import Path

from mcp_runtime_server.types import EnvironmentConfig  
from mcp_runtime_server.environments import create_environment, cleanup_environment