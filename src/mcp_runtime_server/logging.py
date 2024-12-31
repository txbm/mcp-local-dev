"""Logging configuration and test output formatting."""
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import structlog
from structlog.types import Processor, EventDict
from structlog.processors import JSONRenderer

STDERR_LOG_LEVEL = "INFO"
IGNORED_LOGGERS = [
    "mcp.server.session",
    "mcp.server.stdio",
    "aiohttp",
    "asyncio"
]

def add_timestamp(_, __, event_dict: EventDict) -> EventDict:
    """Add ISO timestamp to the event dict."""
    if 'timestamp' not in event_dict:
        import datetime
        event_dict['timestamp'] = datetime.datetime.utcnow().isoformat()
    return event_dict

def add_caller_info(logger: Any, name: str, event_dict: EventDict) -> EventDict:
    """Add caller info to the event dict."""
    import inspect
    frame = inspect.currentframe()
    if frame is not None:
        caller = frame.f_back
        while caller and any(ignored in caller.f_code.co_filename for ignored in IGNORED_LOGGERS):
            caller = caller.f_back
        if caller:
            event_dict.update({
                "module": caller.f_code.co_name,
                "line": caller.f_lineno,
                "file": caller.f_code.co_filename.split("/")[-1]
            })
    return event_dict

def level_filter(logger: Any, name: str, event_dict: EventDict) -> EventDict:
    """Filter log records based on level."""
    try:
        if not any(ignored in logger.name for ignored in IGNORED_LOGGERS):
            level_no = getattr(logging, event_dict.get('level', 'NOTSET'))
            min_level = getattr(logging, STDERR_LOG_LEVEL)
            if level_no >= min_level:
                return event_dict
        raise structlog.DropEvent
    except AttributeError:
        return event_dict

class CompactJSONRenderer:
    """Single-line JSON renderer with minimal output."""
    def __call__(self, _: Any, __: str, event_dict: EventDict) -> str:
        items = {
            "ts": event_dict.pop("timestamp", None),
            "lvl": event_dict.pop("level", "???"),
            "msg": event_dict.pop("event", ""),
            **{k:v for k,v in event_dict.items() if k in ('module', 'line', 'file')}
        }
        if other := {k:v for k,v in event_dict.items() if k not in ('module', 'line', 'file')}:
            items["data"] = other
        return json.dumps(items, separators=(',', ':'))

def configure_logging(level: str = "INFO") -> None:
    """Configure structured logging for the application.
    
    This sets up:
    - STDERR: JSON format, filtered by level & ignored loggers
    - STDOUT: Regular console output for server messages
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=getattr(logging, level)
    )

    # Different processors for STDERR vs STDOUT
    stderr_processors: List[Processor] = [
        level_filter,
        structlog.stdlib.add_log_level,
        add_timestamp,
        add_caller_info,
        CompactJSONRenderer()
    ]

    stdout_processors: List[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(colors=True)
    ]

    structlog.configure(
        processors=stderr_processors if sys.stderr.isatty() else stdout_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)

@dataclass
class TestCase:
    name: str
    status: str
    output: List[str]
    failure_message: Optional[str] = None

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
        r"=+ (\\d+) passed,? (\\d+) failed,? (\\d+) skipped",
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
    return [types.TextContent(
        text=json.dumps({
            "success": True,
            "frameworks": [{
                "framework": framework,
                **results
            }]
        }),
        type="text"
    )]