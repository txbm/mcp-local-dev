"""MCP Runtime Server logging configuration."""
import logging
import sys

def configure_logging():
    """Configure logging for MCP Runtime Server."""
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)
            
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    root.setLevel(logging.DEBUG)
    root.addHandler(handler)

def get_logger(name):
    """Get a logger for a specific module."""
    return logging.getLogger(f"mcp_runtime_server.{name}")