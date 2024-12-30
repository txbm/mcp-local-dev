"""Basic error handling."""
import logging
from typing import Dict, Any


logger = logging.getLogger(__name__) 


class RuntimeServerError(Exception):
    """Base class for runtime server errors."""
    pass


class EnvironmentError(RuntimeServerError):
    """Error creating or managing environments."""
    pass


class BinaryNotFoundError(RuntimeServerError):
    """Required binary not found."""
    pass


class SandboxError(RuntimeServerError):
    """Error in sandbox operations."""
    pass


def log_error(error: Exception, context: Dict[str, Any], logger: logging.Logger) -> None:
    """Log an error with context."""
    logger.error(str(error), extra={"data": context}, exc_info=True)