"""Test result parsing and formatting."""
import json
import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import mcp.types as types

logger = logging.getLogger("mcp_runtime_server.testing.results")

@dataclass
class TestCase:
    name: str 
    status: str
    output: List[str]
    nodeid: str
    duration: float
    failure_message: Optional[str] = None

def parse_pytest_output(stdout: str, stderr: str) -> Dict[str, Any]:
    """Parse pytest JSON output into structured format.

    Args:
        stdout: Raw stdout from pytest run
        stderr: Raw stderr from pytest run
        
    Returns:
        Structured test results dictionary
    """
    try:
        # Load JSON report file
        with open('report.json', 'r') as f:
            report = json.load(f)
            
        # Log each test result
        for test in report.get('report', {}).get('tests', []):
            logger.info(json.dumps({
                'status': test['outcome'],
                'name': test['nodeid'],
                'duration': test['duration'],
                'stdout': test.get('stdout', ''),
                'stderr': test.get('stderr', ''),
            }))
        
        # Extract key data
        summary = report.get('report', {}).get('summary', {})
        tests = report.get('report', {}).get('tests', [])
        
        test_cases = []
        failures = []
        
        for test in tests:
            case = TestCase(
                name=test['nodeid'],
                status=test['outcome'],
                output=test.get('stdout', '').splitlines(),
                nodeid=test['nodeid'],
                duration=test['duration'],
                failure_message=test.get('call', {}).get('longrepr', None) if test['outcome'] == 'failed' else None
            )
            test_cases.append(case)
            if case.failure_message:
                failures.append(case.failure_message)
                
        result = {
            "success": len(failures) == 0,
            "passed": summary.get('passed', 0),
            "failed": summary.get('failed', 0),
            "skipped": summary.get('skipped', 0),
            "total": summary.get('total', 0),
            "failures": failures,
            "stdout": stdout,
            "stderr": stderr,
            "warnings": [],
            "test_cases": [
                {
                    "name": t.name,
                    "status": t.status,
                    "output": t.output,
                    "nodeid": t.nodeid,
                    "duration": t.duration,
                    "failureMessage": t.failure_message
                }
                for t in test_cases
            ],
            "duration": report.get('duration', 0),
        }
        
        # Log summary
        logger.info(json.dumps({
            "summary": {
                "total": result["total"],
                "passed": result["passed"],
                "failed": result["failed"],
                "skipped": result["skipped"],
                "duration": result["duration"]
            }
        }))
        
        return result
        
    except Exception as e:
        logger.error("Failed to parse test results", extra={
            'data': {'error': str(e)}
        })
        raise RuntimeError(f"Failed to parse test results: {str(e)}")

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