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
        stream=sys.stdout,
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
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)

def parse_pytest_output(stdout: str, stderr: str) -> Dict[str, Any]:
    """Parse pytest output into structured format."""
    test_cases = []
    current_test = None
    output_buffer = []

    for line in stdout.splitlines():
        test_match = re.match(r"^(.+?)\s+(PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS)", line)
        if test_match:
            if current_test:
                current_test.output = output_buffer
                test_cases.append(current_test)
            
            name, status = test_match.groups()
            current_test = TestCase(
                name=name.strip(),
                status=status.lower(),
                output=[],
                failure_message=None
            )
            output_buffer = []
            continue

        if current_test:
            if "E   " in line:
                current_test.failure_message = line.split("E   ", 1)[1]
            elif line.strip():
                output_buffer.append(line)

    if current_test:
        current_test.output = output_buffer
        test_cases.append(current_test)

    summary_match = re.search(
        r"=+ (\d+) passed,? (\d+) failed,? (\d+) skipped",
        stdout
    )
    if summary_match:
        passed, failed, skipped = map(int, summary_match.groups())
    else:
        passed = len([t for t in test_cases if t.status == "passed"])
        failed = len([t for t in test_cases if t.status == "failed"])
        skipped = len([t for t in test_cases if t.status == "skipped"])

    total = passed + failed + skipped
    
    # Extract warnings from stderr
    warnings = []
    warning_buffer = []
    in_warning = False
    
    for line in stderr.splitlines():
        if line.startswith("Warning"):
            if warning_buffer:
                warnings.append(" ".join(warning_buffer))
            warning_buffer = [line]
            in_warning = True
        elif in_warning and line.strip():
            warning_buffer.append(line.strip())
        else:
            in_warning = False
            
    if warning_buffer:
        warnings.append(" ".join(warning_buffer))

    return {
        "success": failed == 0,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total": total,
        "failures": [t.failure_message for t in test_cases if t.failure_message],
        "stdout": stdout,
        "stderr": stderr,
        "warnings": warnings,
        "test_cases": [
            {
                "name": t.name,
                "status": t.status,
                "output": t.output,
                "failureMessage": t.failure_message
            }
            for t in test_cases
        ]
    }