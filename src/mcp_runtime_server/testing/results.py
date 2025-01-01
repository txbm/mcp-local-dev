"""Test result parsing and formatting."""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import mcp.types as types
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TestCase:
    name: str
    status: str
    output: List[str]
    failure_message: Optional[str] = None
    duration: Optional[float] = None


def parse_pytest_json(report: Dict[str, Any]) -> Dict[str, Any]:
    """Parse pytest JSON output.

    Args:
        report: Parsed JSON report from pytest

    Returns:
        Structured test results dictionary
    """
    tests = report.get("tests", [])
    summary = report.get("summary", {})

    test_cases = []
    failures = []

    for test in tests:
        status = test.get("outcome")
        failure = test.get("call", {}).get("longrepr") if status == "failed" else None

        case = TestCase(
            name=test.get("nodeid"),
            status=status,
            output=test.get("stdout", "").splitlines(),
            failure_message=failure,
            duration=test.get("duration"),
        )
        test_cases.append(case)

        if failure:
            failures.append(failure)

    result = {
        "success": len(failures) == 0,
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "skipped": summary.get("skipped", 0),
        "total": summary.get("total", 0),
        "failures": failures,
        "test_cases": [
            {
                "name": t.name,
                "status": t.status,
                "output": t.output,
                "failure_message": t.failure_message,
                "duration": t.duration,
            }
            for t in test_cases
        ],
        "duration": report.get("duration", 0),
        "warnings": report.get("warnings", []),
    }

    logger.info(
        {
            "event": "test_summary",
            "data": {
                "total": result["total"],
                "passed": result["passed"],
                "failed": result["failed"],
                "skipped": result["skipped"],
            },
        }
    )

    return result


def format_test_results(
    framework: str, results: Dict[str, Any]
) -> list[types.TextContent]:
    """Convert parsed test results into MCP-compatible format."""
    return [
        types.TextContent(
            text=json.dumps(
                {"success": True, "frameworks": [{"framework": framework, **results}]}
            ),
            type="text",
        )
    ]
