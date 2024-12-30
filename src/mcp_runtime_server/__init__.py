"""MCP Runtime Server."""
# Core types
from mcp_runtime_server.types import (
    RuntimeManager, 
    EnvironmentConfig,
    Environment
)

# Core functionality
from mcp_runtime_server.environments import (
    create_environment,
    cleanup_environment
)
from mcp_runtime_server.testing.execution import auto_run_tests