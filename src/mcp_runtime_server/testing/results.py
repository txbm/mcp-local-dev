"""Test result parsing and formatting."""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from mcp.types import TextContent
from mcp_runtime_server.types import TestCase
from mcp_runtime_server.logging import get_logger

logger = get_logger(__name__)



def parse_pytest_json(report: Dict[str, Any]) -> Dict[str, Any]:
    """Transform pytest JSON output into structured results"""
    if not isinstance(report, dict):
        logger.error({"event": "invalid_pytest_report", "error": "Report must be a dictionary"})
        raise ValueError("Invalid pytest report format")
        
    tests = report.get("tests", [])
    if not isinstance(tests, list):
        logger.error({"event": "invalid_pytest_tests", "error": "Tests must be a list"})
        raise ValueError("Invalid pytest tests format")
        
    summary = report.get("summary", {})
    if not isinstance(summary, dict):
        logger.error({"event": "invalid_pytest_summary", "error": "Summary must be a dictionary"})
        raise ValueError("Invalid pytest summary format")

    def create_test_case(test: Dict[str, Any]) -> TestCase:
        status = test.get("outcome")
        failure = test.get("call", {}).get("longrepr") if status == "failed" else None
        return TestCase(
            name=test.get("nodeid"),
            status=status,
            output=test.get("stdout", "").splitlines(),
            failure_message=failure,
            duration=test.get("duration"),
        )

    test_cases = [create_test_case(test) for test in tests]
    failures = [case.failure_message for case in test_cases if case.failure_message]

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
) -> list[TextContent]:
    """Convert parsed test results into MCP-compatible format."""
    return [
        TextContent(
            text=json.dumps(
                {"success": True, "frameworks": [{"framework": framework, **results}]}
            ),
            type="text",
        )
    ]
