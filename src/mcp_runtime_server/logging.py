"""Logging configuration and test output formatting."""
import json
import logging
import sys
from typing import Any, Dict
from pathlib import Path

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

class JsonFormatter(logging.Formatter):
    """Format logs as single-line JSON with colors."""
    COLORS = {
        "DEBUG": ColorCodes.BLUE,
        "INFO": ColorCodes.GREEN,
        "WARNING": ColorCodes.YELLOW,
        "ERROR": ColorCodes.RED + ColorCodes.BOLD,
        "CRITICAL": ColorCodes.MAGENTA + ColorCodes.BOLD
    }

    def __init__(self):
        super().__init__()
        self.include_source = True

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as color-coded JSON."""
        color = self.COLORS.get(record.levelname, "")

        # Extract caller info if available
        try:
            caller_frame = sys._getframe(8)  # Adjust frame depth as needed
            module = Path(caller_frame.f_code.co_filename).name
            lineno = caller_frame.f_lineno
            func = caller_frame.f_code.co_name
            location = f"{module}:{lineno} in {func}"
        except (AttributeError, ValueError):
            location = None

        # Build output
        output = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "msg": record.getMessage(),
        }

        if location and self.include_source:
            output["source"] = location

        # Include any additional fields from record
        if hasattr(record, "data"):
            output["data"] = record.data

        # Apply color codes
        json_str = json.dumps(output)
        return f"{color}{json_str}{ColorCodes.RESET}"

def configure_logging():
    """Configure application logging."""
    # Create stderr handler with JSON formatting
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(JsonFormatter())
    stderr_handler.setLevel(logging.INFO)

    # Configure root logger for MCP protocol on stdout only
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Configure app logger for everything else on stderr
    app_logger = logging.getLogger("mcp_local_dev")
    app_logger.setLevel(logging.INFO)
    app_logger.addHandler(stderr_handler)
    app_logger.propagate = False

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(f"mcp_runtime_server.{name}")

def log_with_data(logger: logging.Logger, level: int, msg: str, data: Dict[str, Any] = None):
    """Log a message with optional structured data."""
    if data:
        logger = logger.makeRecord(
            logger.name, level, "(unknown)", 0, msg, (), None, extra={"data": data}
        )
    logger.log(level, msg)
