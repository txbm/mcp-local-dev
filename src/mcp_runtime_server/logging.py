"""MCP Runtime Server logging configuration."""
import json
import logging
import sys
from datetime import datetime

class JsonFormatter(logging.Formatter):
    """Format log records as JSON with color-coding."""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }

    def format(self, record):
        """Format the log record as a colored JSON string."""
        # Extract basic fields
        message_dict = {
            'time': self.formatTime(record),
            'level': record.levelname,
            'source': f"{record.pathname}:{record.lineno}",
            'message': record.getMessage()
        }

        # Add extra fields if present
        if hasattr(record, 'data'):
            message_dict['data'] = record.data

        # Add exception info if present
        if record.exc_info:
            message_dict['exc_info'] = self.formatException(record.exc_info)

        # Apply color coding
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']

        # Format as indented JSON with color
        return f"{color}{json.dumps(message_dict, indent=2)}{reset}"

class EventFilter(logging.Filter):
    """Filter to ensure proper event context."""

    def filter(self, record):
        """Add pathname and line number if not present."""
        if not hasattr(record, 'pathname'):
            record.pathname = record.filename
        if not hasattr(record, 'lineno'):
            record.lineno = 0
        return True

def configure_logging():
    """Configure logging with JSON formatting and color output.
    
    Per Python logging docs, this should be called once at application startup.
    """
    # Clear any existing handlers
    root = logging.getLogger()
    root.handlers.clear()
    
    # Setup handler with JSON formatting
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(EventFilter())
    
    # Configure root logger
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)

def get_logger(name):
    """Get a logger instance for a module.
    
    Args:
        name: Module name, typically __name__
        
    Returns:
        Logger instance configured for the module
    """
    logger = logging.getLogger(f"mcp_runtime_server.{name}")
    return logger