"""Logging configuration for MCP Runtime Server."""
import json
import logging
import logging.config
from datetime import datetime
from typing import Any, Dict

class ColorFormatter(logging.Formatter):
    """Custom formatter with color support."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m'  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with color and as JSON."""
        # Add source file info
        record.source_info = f"{record.filename}:{record.lineno}"
        
        # Create the base log object
        log_object = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'logger': record.name,
            'level': record.levelname,
            'source': record.source_info,
            'message': record.getMessage()
        }
        
        # Add exception info if present
        if record.exc_info:
            log_object['exception'] = self.formatException(record.exc_info)

        # Add any extra fields
        if hasattr(record, 'data'):
            log_object['data'] = record.data

        # Format as colored JSON
        color = self.COLORS.get(record.levelname, '')
        formatted = json.dumps(log_object, indent=None)
        return f"{color}{formatted}{self.RESET}"

def configure_logging(level: str = 'INFO') -> None:
    """Configure logging with color and JSON formatting."""
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'colored_json': {
                '()': ColorFormatter
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'colored_json',
                'stream': 'ext://sys.stdout'
            }
        },
        'loggers': {
            'mcp_runtime_server': {
                'handlers': ['console'],
                'level': level,
                'propagate': False
            }
        },
        'root': {
            'handlers': ['console'],
            'level': level
        }
    }
    
    logging.config.dictConfig(config)

def log_with_data(logger: logging.Logger, level: int, msg: str, data: Dict[str, Any] = None) -> None:
    """Helper to log messages with structured data."""
    extra = {'data': data} if data else {}
    logger.log(level, msg, extra=extra)