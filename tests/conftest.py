"""Test configuration and fixtures."""
import pytest
from mcp_runtime_server import EnvironmentConfig
from mcp_runtime_server.environments import create_environment, cleanup_environment