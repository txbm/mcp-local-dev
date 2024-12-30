"""Simplified error handling for MCP runtime server."""
from typing import Any, Dict, Optional
from mcp.types import (
    ErrorData,
    PARSE_ERROR,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    INVALID_PARAMS,
    INTERNAL_ERROR
)


class RuntimeServerError(Exception):
    """Base error class for runtime server with standardized error handling."""

    def __init__(
        self, 
        message: str, 
        code: int = INTERNAL_ERROR, 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.code = code
        self.details = details or {}

    def to_error_data(self) -> ErrorData:
        """Convert error to standard ErrorData format."""
        return ErrorData(
            code=self.code,
            message=str(self),
            data=self.details
        )


class InvalidEnvironmentError(RuntimeServerError):
    """Error when an environment is invalid or not found."""
    def __init__(self, env_id: str):
        super().__init__(
            f"Environment {env_id} not found",
            code=INVALID_PARAMS,
            details={"env_id": env_id}
        )


class ResourceLimitError(RuntimeServerError):
    """Error when a resource limit is exceeded."""
    def __init__(self, resource_type: str, limit: Any, current: Any):
        super().__init__(
            f"Resource limit exceeded for {resource_type}",
            code=INTERNAL_ERROR,
            details={
                "resource_type": resource_type,
                "limit": limit,
                "current": current
            }
        )


class BinaryNotFoundError(RuntimeServerError):
    """Error when a required binary is not found."""
    def __init__(self, binary_name: str):
        super().__init__(
            f"Binary {binary_name} not found",
            code=INVALID_REQUEST,
            details={"binary_name": binary_name}
        )


class SandboxError(RuntimeServerError):
    """Error related to sandbox operations."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=INTERNAL_ERROR, details=details)
