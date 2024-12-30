"""Logging configuration for MCP Runtime Server."""
import json
import logging
import logging.config
import sys
from datetime import datetime
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging to stderr."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
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

        # Format as JSON
        return json.dumps(log_object)


class StderrFilter(logging.Filter):
    """Filter to only allow DEBUG level messages."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Return True only for DEBUG level messages."""
        return record.levelno == logging.DEBUG


def configure_logging() -> None:
    """Configure logging to send only debug messages to stderr as JSON."""
    config = {
        'version': 1,
        'disable_existing_loggers': True,  # Disable existing loggers to prevent stdout usage
        'formatters': {
            'json': {
                '()': JsonFormatter
            }
        },
        'filters': {
            'debug_only': {
                '()': StderrFilter
            }
        },
        'handlers': {
            'stderr': {
                'class': 'logging.StreamHandler',
                'formatter': 'json',
                'stream': 'ext://sys.stderr',
                'filters': ['debug_only']
            }
        },
        'loggers': {
            'mcp_runtime_server': {
                'handlers': ['stderr'],
                'level': 'DEBUG',
                'propagate': False
            }
        },
        'root': {
            'handlers': ['stderr'],
            'level': 'DEBUG'
        }
    }
    
    # Clear any existing handlers to ensure clean configuration
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    logging.config.dictConfig(config)


def log_with_data(logger: logging.Logger, level: int, msg: str, data: Dict[str, Any] = None) -> None:
    """Helper to log messages with structured data."""
    extra = {'data': data} if data else {}
    logger.log(level, msg, extra=extra)