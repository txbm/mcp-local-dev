"""Logging configuration and test output formatting."""
import logging
import re
import sys
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TextIO, Union

import structlog

@dataclass
class TestCase:
    name: str
    status: str
    output: List[str]
    failure_message: Optional[str] = None

def configure_logging(level: str = "INFO") -> None:
    """Configure structured logging for the application."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=getattr(logging, level)
    )

    renderer = structlog.processors.JSONRenderer() if sys.stderr.isatty() else structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str) -> structlog.stdlib.BoundLogger:
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

def format_test_results(framework: str, results: Dict[str, Any]) -> List[types.TextContent]:
    """Convert parsed test results into MCP-compatible format."""
    from mcp.types import TextContent
    return [TextContent(
        text=json.dumps({
            "success": True,
            "frameworks": [{
                "framework": framework,
                **results
            }]
        }),
        type="text"
    )]