"""Logging configuration and test output formatting."""
import logging
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TextIO

import structlog
from structlog.processors import TimeStamper, StackInfoRenderer, format_exc_info, EventRenamer
from structlog.stdlib import LoggerFactory, BoundLogger

@dataclass
class TestCase:
    name: str
    status: str
    output: List[str]
    failure_message: Optional[str] = None

def configure_logging(level: str = "INFO") -> None:
    """Configure structured logging for the application."""
    # Set up standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=getattr(logging, level)
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            TimeStamper(fmt="iso"),
            StackInfoRenderer(),
            format_exc_info,
            structlog.dev.ConsoleRenderer(colors=True)
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stderr),
        cache_logger_on_first_use=True,
    )