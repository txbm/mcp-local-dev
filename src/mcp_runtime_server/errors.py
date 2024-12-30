"""Error logging utilities."""
import traceback
import logging
from typing import Dict, Any


def log_error(error: Exception, context: Dict[str, Any], logger: logging.Logger) -> None:
    """Log an error with context and traceback."""
    logger.error(
        "Error occurred",
        extra={
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            **context
        }
    )