"""Error handling for MCP runtime server."""
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
    """Base class for runtime server errors."""

    def __init__(self, message: str, code: int = INTERNAL_ERROR):
        super().__init__(message)
        self.code = code

    def as_error_data(self) -> ErrorData:
        """Convert to MCP error data."""
        return ErrorData(
            code=self.code,
            message=str(self),
            data=None
        )


class InvalidEnvironmentError(RuntimeServerError):
    """Error when an environment is invalid or not found."""
    def __init__(self, env_id: str):
        super().__init__(
            f"Environment {env_id} not found",
            code=INVALID_PARAMS
        )


class ResourceLimitError(RuntimeServerError):
    """Error when a resource limit is exceeded."""
    def __init__(self, message: str, resource_type: str, limit: Any, current: Any):
        super().__init__(
            message,
            code=INTERNAL_ERROR
        )
        self.data = {
            "resource_type": resource_type,
            "limit": limit,
            "current": current
        }

    def as_error_data(self) -> ErrorData:
        return ErrorData(
            code=self.code,
            message=str(self),
            data=self.data
        )


class BinaryNotFoundError(RuntimeServerError):
    """Error when a required binary is not found."""
    def __init__(self, binary_name: str):
        super().__init__(
            f"Binary {binary_name} not found",
            code=INTERNAL_ERROR
        )


class SandboxError(RuntimeServerError):
    """Error related to sandbox operations."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=INTERNAL_ERROR)
        self.data = details

    def as_error_data(self) -> ErrorData:
        return ErrorData(
            code=self.code,
            message=str(self),
            data=self.data
        )