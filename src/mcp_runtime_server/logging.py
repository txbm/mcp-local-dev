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

# Don't modify root logger - mcp server uses it for stdout
root = logging.getLogger()
root.handlers = []

# Setup stderr handler
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.INFO)

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
    if frame:
        caller = frame.f_back
        while caller:
            filename = caller.f_code.co_filename
            if '/mcp/' not in filename and not any(x in filename for x in ['asyncio', 'aiohttp']):
                event_dict.update({
                    'module': caller.f_code.co_name,
                    'file': filename.split('/')[-1],
                    'line': caller.f_lineno
                })
                break
            caller = caller.f_back
    return event_dict

class StderrRenderer:
    """Render log entries as single-line JSON with colors."""
    def __call__(self, _: Any, __: str, event_dict: EventDict) -> str:
        # Extract standard fields
        level = event_dict.pop('level', 'INFO')
        timestamp = event_dict.pop('timestamp', None)
        event = event_dict.pop('event', '')
        module = event_dict.pop('module', None) 
        filename = event_dict.pop('file', None)
        lineno = event_dict.pop('line', None)
        
        # Build output
        output = {
            'ts': timestamp,
            'lvl': level,
            'msg': event
        }
        
        # Add location if available
        if module and filename and lineno:
            output['loc'] = f"{filename}:{lineno} in {module}"
            
        # Add remaining fields as data
        if event_dict:
            output['data'] = event_dict

        return json.dumps(output)

def configure_logging() -> None:
    """Configure structured logging for the application."""
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            add_timestamp,
            add_caller_info,
            structlog.processors.format_exc_info,
            StderrRenderer()
        ],
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