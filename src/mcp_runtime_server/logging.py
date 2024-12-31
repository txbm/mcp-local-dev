"""Logging configuration for MCP Runtime Server."""
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, Union

COLORS = {
    'DEBUG': '\033[36m',     
    'INFO': '\033[32m',      
    'WARNING': '\033[33m',   
    'ERROR': '\033[31m',     
    'CRITICAL': '\033[35m',  
    'RESET': '\033[0m'       
}

class JsonFormatter(logging.Formatter):
    """Formats log records as colored JSON with source info."""
    
    def __init__(self):
        super().__init__()
        self.default_msec_format = '%s.%03d'

    def format(self, record):
        log_obj = {
            'timestamp': self.formatTime(record, self.default_msec_format),
            'logger': record.name,
            'level': record.levelname,
            'source': f"{record.module}:{record.lineno}",
            'message': record.getMessage(),
            'thread': record.threadName,
            'process': record.processName
        }

        if record.exc_info:
            log_obj['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }

        if hasattr(record, 'data'):
            log_obj['data'] = record.data

        color = COLORS.get(record.levelname, '')
        reset = COLORS['RESET'] if color else ''
        return f"{color}{json.dumps(log_obj)}{reset}"

def configure_logging():
    """Configure JSON formatted logging to stderr."""
    # Remove existing handlers
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)

    # Create handler
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    handler.setLevel(logging.DEBUG)

    # Configure root logger
    root.setLevel(logging.DEBUG)
    root.addHandler(handler)

    # Configure package logger
    logger = logging.getLogger('mcp_runtime_server')
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger.addHandler(handler)

def log_with_data(
    logger: logging.Logger,
    level: int,
    msg: str,
    data: Optional[Dict[str, Any]] = None,
    exc_info: Optional[Union[bool, Tuple[type, Exception, Any]]] = None
) -> None:
    """Log a message with optional structured data and exception info."""
    extra = {'data': data} if data else None
    logger.log(level, msg, exc_info=exc_info, extra=extra)

# Convenience methods
def log_request_start(logger: logging.Logger, tool: str, **kwargs) -> None:
    """Log tool request start."""
    log_with_data(logger, logging.DEBUG, f"Tool request started: {tool}", {
        "tool": tool,
        "arguments": kwargs,
        "event": "request_start"
    })

def log_request_end(logger: logging.Logger, tool: str, result: Any, **kwargs) -> None:
    """Log tool request completion."""
    log_with_data(logger, logging.DEBUG, f"Tool request completed: {tool}", {
        "tool": tool,
        "result": result,
        "arguments": kwargs,
        "event": "request_end"
    })

def log_request_error(logger: logging.Logger, tool: str, error: Exception, **kwargs) -> None:
    """Log tool request error."""
    log_with_data(
        logger,
        logging.ERROR,
        f"Tool request failed: {tool}",
        {
            "tool": tool,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "arguments": kwargs,
            "event": "request_error"
        },
        exc_info=True
    )