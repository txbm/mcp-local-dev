"""MCP Runtime Server logging configuration."""
import json
import logging
import sys
from datetime import datetime

class JsonFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }

    def format(self, record):
        message_dict = {
            'time': self.formatTime(record),
            'level': record.levelname,
            'source': f"{record.pathname}:{record.lineno}",
            'message': record.getMessage()
        }
        if hasattr(record, 'data'):
            message_dict['data'] = record.data
        if record.exc_info:
            message_dict['exc_info'] = self.formatException(record.exc_info)
        return f"{self.COLORS.get(record.levelname, '')}{json.dumps(message_dict)}{self.COLORS['RESET']}"

class NoResourcesFilter(logging.Filter):
    def filter(self, record):
        skip_messages = ['ListResourcesRequest', 'ListPromptsRequest']
        return not any(msg in record.getMessage() for msg in skip_messages)

def configure_logging():
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(NoResourcesFilter())
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)

def get_logger(name):
    return logging.getLogger(f"mcp_runtime_server.{name}")