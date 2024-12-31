"""MCP Runtime Server logging configuration."""
import json
import logging
import sys
from datetime import datetime

class JsonFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m', 
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[35m',
        'RESET': '\033[0m'
    }

    def format(self, record):
        message_dict = {
            'time': self.formatTime(record),
            'level': record.levelname,
            'source': f"{record.module}:{record.lineno}",
            'message': record.getMessage()
        }
        if hasattr(record, 'data'):
            message_dict['data'] = record.data
        if record.exc_info:
            message_dict['exc_info'] = self.formatException(record.exc_info)
        if hasattr(record, 'test_info'):
            message_dict['test_info'] = record.test_info
        if hasattr(record, 'command'):
            message_dict['command'] = record.command
            if hasattr(record, 'cwd'):
                message_dict['cwd'] = record.cwd
            if hasattr(record, 'env'):
                message_dict['env'] = {k: v for k, v in record.env.items() if not k.startswith('_')}
        if hasattr(record, 'stdout'):
            message_dict['stdout'] = record.stdout
        if hasattr(record, 'stderr'):
            message_dict['stderr'] = record.stderr
        if hasattr(record, 'exit_code'):
            message_dict['exit_code'] = record.exit_code
            
        return f"{self.COLORS.get(record.levelname, '')}{json.dumps(message_dict)}{self.COLORS['RESET']}"

class MessageFilter(logging.Filter):
    def filter(self, record):
        if record.name.startswith('mcp.server.lowlevel'):
            return False
        skip_messages = ['ListResourcesRequest', 'ListPromptsRequest']
        return not any(msg in record.getMessage() for msg in skip_messages)

def configure_logging():
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(MessageFilter())
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)

def get_logger(name):
    return logging.getLogger(f"mcp_runtime_server.{name}")
