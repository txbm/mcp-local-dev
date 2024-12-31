"""Logging configuration for MCP Runtime Server."""
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, Union

class JsonFormatter(logging.Formatter):
    def format(self, record):
        record.message = record.getMessage()
        
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
            
        data = {
            'time': record.asctime,
            'name': record.name,
            'level': record.levelname,
            'message': record.message
        }
        
        if record.exc_info:
            data['exc_info'] = self.formatException(record.exc_info)
            
        if hasattr(record, 'data'):
            data['data'] = record.data
            
        return json.dumps(data)

def configure_logging():
    """Configure logging for the MCP Runtime Server."""
    logger = logging.getLogger('mcp_runtime_server')
    logger.setLevel(logging.DEBUG)
    
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s'))
    
    logger.addHandler(handler)

def get_logger(name):
    """Get a logger for a specific module."""
    return logging.getLogger(f'mcp_runtime_server.{name}')