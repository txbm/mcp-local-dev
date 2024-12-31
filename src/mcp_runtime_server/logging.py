"""Logging configuration for MCP Runtime Server."""
import json
import logging
import logging.config
import inspect
import sys
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, Union

# ANSI color codes
COLORS = {
    'DEBUG': '\033[36m',     # Cyan
    'INFO': '\033[32m',      # Green
    'WARNING': '\033[33m',   # Yellow
    'ERROR': '\033[31m',     # Red
    'CRITICAL': '\033[35m',  # Magenta
    'RESET': '\033[0m'       # Reset
}

class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging to stderr."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Get the caller's frame info
        frame = inspect.currentframe()
        calling_frame = None
        try:
            while frame:
                if frame.f_code.co_filename != __file__:
                    calling_frame = frame
                    break
                frame = frame.f_back
        finally:
            del frame
        
        if calling_frame:
            record.filename = calling_frame.f_code.co_filename.split('/')[-1]
            record.lineno = calling_frame.f_lineno
            record.module = calling_frame.f_code.co_name

        # Add source file info
        record.source_info = f"{record.filename}:{record.lineno}"
        
        # Create the base log object with more detailed information
        log_object = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'logger': record.name,
            'level': record.levelname,
            'source': record.source_info,
            'message': record.getMessage(),
            'thread': record.threadName,
            'process': record.processName
        }
        
        # Add exception info if present
        if record.exc_info:
            exception_type, exception_value = record.exc_info[:2]
            log_object['exception'] = {
                'type': exception_type.__name__,
                'message': str(exception_value),
                'traceback': self.formatException(record.exc_info)
            }

        # Add any extra fields
        if hasattr(record, 'data'):
            try:
                json.dumps(record.data)
                log_object['data'] = record.data
            except (TypeError, ValueError):
                log_object['data'] = self._sanitize_data(record.data)
        
        # Format as compact JSON and add color
        color = COLORS.get(record.levelname, '')
        reset = COLORS['RESET'] if color else ''
        return f"{color}{json.dumps(log_object)}{reset}"
    
    def _sanitize_data(self, data: Any) -> Any:
        """Recursively sanitize data to ensure JSON serialization is possible."""
        if isinstance(data, (str, int, float, bool, type(None))):
            return data
        elif isinstance(data, (list, tuple)):
            return [self._sanitize_data(item) for item in data]
        elif isinstance(data, dict):
            return {
                str(key): self._sanitize_data(value) 
                for key, value in data.items()
            }
        elif hasattr(data, '__dict__'):
            return self._sanitize_data(data.__dict__)
        else:
            return str(data)


class StderrFilter(logging.Filter):
    """Filter to control which messages go to stderr."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Allow DEBUG level and above messages for better visibility during development."""
        return True


def configure_logging() -> None:
    """Configure logging to send structured logs to stderr."""
    config = {
        'version': 1,
        'disable_existing_loggers': True,  # Disable existing loggers to prevent stdout usage
        'formatters': {
            'json': {
                '()': JsonFormatter
            }
        },
        'filters': {
            'stderr_filter': {
                '()': StderrFilter
            }
        },
        'handlers': {
            'stderr': {
                'class': 'logging.StreamHandler',
                'formatter': 'json',
                'stream': sys.stderr,
                'filters': ['stderr_filter'],
                'level': 'DEBUG'
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


def log_with_data(
    logger: logging.Logger, 
    level: int, 
    msg: str, 
    data: Optional[Dict[str, Any]] = None,
    exc_info: Union[bool, Tuple[Any, BaseException, Any]] = None
) -> None:
    """Enhanced helper to log messages with structured data and optional exception info."""
    extra = {'data': data} if data else {}
    extra['_frame'] = inspect.currentframe().f_back
    logger.log(level, msg, extra=extra, exc_info=exc_info)


# Add convenience methods for common logging patterns
def log_request_start(logger: logging.Logger, tool: str, **kwargs) -> None:
    """Log the start of a tool request with context."""
    log_with_data(logger, logging.DEBUG, f"Tool request started: {tool}", {
        "tool": tool,
        "arguments": kwargs,
        "event": "request_start"
    })


def log_request_end(logger: logging.Logger, tool: str, result: Any, **kwargs) -> None:
    """Log the successful completion of a tool request."""
    log_with_data(logger, logging.DEBUG, f"Tool request completed: {tool}", {
        "tool": tool,
        "result": result,
        "arguments": kwargs,
        "event": "request_end"
    })


def log_request_error(
    logger: logging.Logger,
    tool: str,
    error: Exception,
    **kwargs
) -> None:
    """Log a tool request error with full context."""
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