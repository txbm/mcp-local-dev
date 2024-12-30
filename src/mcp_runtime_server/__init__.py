"""MCP Runtime Server package."""

from mcp_runtime_server.types import (
    RuntimeManager,
    RuntimeConfig,
    Environment,
    TestConfig,
    TestResult,
    CaptureConfig,
    CaptureMode,
    ResourceLimits,
    CapturedOutput
)
from mcp_runtime_server.sandbox import create_sandbox, cleanup_sandbox
from mcp_runtime_server.binaries import ensure_binary
from mcp_runtime_server.runtime import create_environment, cleanup_environment, run_command
from mcp_runtime_server.errors import (
    RuntimeServerError, 
    EnvironmentError,
    ResourceLimitError,
    BinaryNotFoundError,
    SandboxError
)

__version__ = "0.1.0"

__all__ = [
    # Runtime types
    "RuntimeManager",
    "RuntimeConfig",
    "Environment",
    
    # Testing types
    "TestConfig",
    "TestResult",
    "CapturedOutput",
    
    # Configuration types
    "CaptureConfig", 
    "CaptureMode",
    "ResourceLimits",
    
    # Runtime functions
    "create_environment",
    "cleanup_environment", 
    "run_command",
    
    # Sandbox functions
    "create_sandbox",
    "cleanup_sandbox",
    "ensure_binary",
    
    # Error types
    "RuntimeServerError",
    "EnvironmentError",
    "ResourceLimitError", 
    "BinaryNotFoundError",
    "SandboxError"
]