"""Runtime system interface."""
from mcp_runtime_server.environments import create_environment, cleanup_environment, ENVIRONMENTS
from mcp_runtime_server.commands import run_command
from mcp_runtime_server.execution import auto_run_tests