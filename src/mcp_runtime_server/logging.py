"""Logging configuration for MCP Runtime Server."""
import logging
from typing import Set, Dict, Any

# Requests that should not be logged
SUPPRESSED_REQUESTS: Set[str] = {
    'ListResourcesRequest',
    'ListPromptsRequest'
}

class RequestFilter(logging.Filter):
    """Filter out noisy request logging."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log records.
        
        Args:
            record: Log record to filter
            
        Returns:
            True if record should be logged, False otherwise
        """
        # Check if this is a request processing message
        if 'Processing request of type' in record.msg:
            # Extract request type
            request_type = record.msg.split('type ')[-1]
            return request_type not in SUPPRESSED_REQUESTS
        return True


def log_runtime_error(error: Exception, context: Dict[str, Any]) -> None:
    """Log runtime errors with context.
    
    Args:
        error: The exception that occurred
        context: Additional context information
    """
    logger = logging.getLogger(__name__)
    logger.error(f"Runtime error: {str(error)}", extra={"context": context})


def setup_logging() -> None:
    """Configure logging with request filtering."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Add filter to the root logger
    logging.getLogger('mcp.server.lowlevel.server').addFilter(RequestFilter())
