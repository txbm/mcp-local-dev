"""Basic error handling."""
import logging
from typing import Dict, Any


logger = logging.getLogger(__name__) 


def log_error(error: Exception, context: Dict[str, Any], logger: logging.Logger) -> None:
    """Log an error with context."""
    logger.error(str(error), extra={"data": context}, exc_info=True)