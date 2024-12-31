"""Logging configuration and test output formatting."""
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import structlog
import mcp.types as types
from structlog.types import Processor, EventDict

# Set MCP internal loggers to WARNING level
logging.getLogger("mcp.server").setLevel(logging.WARNING)
logging.getLogger("mcp.shared").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

STDERR_LOG_LEVEL = "INFO"

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
        level_no = getattr(logging, event_dict.get('level', 'NOTSET'))
        min_level = getattr(logging, STDERR_LOG_LEVEL)
        if level_no >= min_level:
            return event_dict
        raise structlog.DropEvent
    except AttributeError:
        return event_dict
    
class StderrJSONRenderer:
    """Single-line JSON renderer for stderr output."""
    def __call__(self, _: Any, __: str, event_dict: EventDict) -> str:
        return json.dumps({
            "ts": event_dict.get("timestamp"),
            "lvl": event_dict.get("level", "INFO"),
            "msg": event_dict.get("event", ""),
            "mod": event_dict.get("module"),
            "ln": event_dict.get("line"),
            "file": event_dict.get("file"),
            **({"data": {k:v for k,v in event_dict.items() if k not in 
                        ('timestamp', 'level', 'event', 'module', 'line', 'file')}} 
               if any(k for k in event_dict if k not in 
                     ('timestamp', 'level', 'event', 'module', 'line', 'file')) else {})
        }, separators=(',', ':'))

def configure_logging() -> None:
    """Configure structured logging for the application."""
    # Basic config for third-party modules
    logging.basicConfig(format="%(message)s", stream=sys.stderr, level=logging.WARNING)

    stderr_processors: List[Processor] = [
        level_filter,
        structlog.stdlib.add_log_level,
        add_timestamp,
        add_caller_info, 
        StderrJSONRenderer()
    ]

    stdout_processors: List[Processor] = [
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