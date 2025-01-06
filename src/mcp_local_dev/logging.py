"""Logging configuration and test output formatting."""

import json
import logging
import sys
from typing import Any, Dict

# Don't modify root logger - MCP server uses it for stdout
root = logging.getLogger()
root.handlers = []


class ColorCodes:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"


LEVEL_COLORS = {
    "DEBUG": ColorCodes.BLUE,
    "INFO": ColorCodes.GREEN,
    "WARNING": ColorCodes.YELLOW,
    "ERROR": ColorCodes.RED + ColorCodes.BOLD,
    "CRITICAL": ColorCodes.MAGENTA + ColorCodes.BOLD,
}


class JsonFormatter(logging.Formatter):
    """Format log records as color-coded JSON."""

    def format(self, record: logging.LogRecord) -> str:
        color = LEVEL_COLORS.get(record.levelname, "")

        output = {
            "ts": record.asctime if hasattr(record, "asctime") else "",
            "level": record.levelname,
            "msg": record.getMessage(),
        }

        if hasattr(record, "data"):
            output["data"] = record.data

        json_str = json.dumps(output)
        return f"{color}{json_str}{ColorCodes.RESET}"


def configure_logging():
    """Set up application logging with JSON formatting."""
    # Get the root logger for mcp_local_dev
    app_logger = logging.getLogger("mcp_local_dev")
    
    # Only configure if not already configured
    if not app_logger.handlers:
        # Create and configure new handler
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(JsonFormatter())
        handler.setLevel(logging.DEBUG)
        
        # Configure logger
        app_logger.setLevel(logging.DEBUG)
        app_logger.addHandler(handler)
        app_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(f"mcp_local_dev.{name}")


def log_with_data(
    logger: logging.Logger, level: int, msg: str, data: Dict[str, Any] = None
):
    """Log a message with optional structured data."""
    if data:
        record = logger.makeRecord(
            logger.name, level, "(unknown)", 0, msg, (), None, extra={"data": data}
        )
        logger.handle(record)
    else:
        logger.log(level, msg)
