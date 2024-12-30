"""Error handling for MCP runtime server."""
import logging
from typing import Any, Dict, Optional
from mcp.types import (
    ErrorData,
    PARSE_ERROR,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    INVALID_PARAMS,
    INTERNAL_ERROR
)

logger = logging.getLogger(__name__)

def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    logger: Optional[logging.Logger] = None
) -> None:
    """Log an error with context."""
    logger = logger or logging.getLogger(__name__)
    
    error_info = {
        "error_type": error.__class__.__name__,
        "error_message": str(error)
    }
    if context:
        error_info["context"] = context
    if isinstance(error, RuntimeServerError):
        error_info["code"] = error.code
        error_info["details"] = error.details
        
    logger.error("Runtime error occurred", extra={"data": error_info})


class RuntimeServerError(Exception):
    """Base error class for runtime server."""
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
        """Convert to ErrorData format."""
        return ErrorData(
            code=self.code,
            message=str(self),
            data=self.details
        )


class InvalidEnvError(RuntimeServerError):
    """Error for invalid/missing environment."""
    def __init__(self, env_id: str):
        super().__init__(
            f"Environment {env_id} not found",
            code=INVALID_PARAMS,
            details={"env_id": env_id}
        )


class ResourceError(RuntimeServerError):
    """Resource limit exceeded error."""
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


class BinNotFoundError(RuntimeServerError):
    """Binary not found error."""
    def __init__(self, binary_name: str):
        super().__init__(
            f"Binary {binary_name} not found",
            code=INVALID_REQUEST,
            details={"binary_name": binary_name}
        )


class SandboxError(RuntimeServerError):
    """Sandbox operation error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=INTERNAL_ERROR, details=details)