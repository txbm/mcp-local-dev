"""Tests for test results parsing."""

import pytest
from mcp_runtime_server.testing.results import parse_pytest_json


def test_parse_pytest_empty():
    """Test parsing empty pytest results."""
    empty_report = {"summary": {}}
    result = parse_pytest_json(empty_report)
    
    assert result["success"] is True
    assert result["total"] == 0
    assert result["passed"] == 0
    assert result["failed"] == 0
    assert result["skipped"] == 0
    assert result["test_cases"] == []


def test_parse_pytest_success():
    """Test parsing successful pytest results."""
    report = {
        "summary": {
            "total": 5,
            "passed": 4,
            "failed": 0,
            "skipped": 1
        },
        "tests": [
            {
                "nodeid": "test_file.py::test_function",
                "outcome": "passed",
                "duration": 0.1
            },
            {
                "nodeid": "test_file.py::TestClass::test_method",
                "outcome": "passed",
                "duration": 0.2
            },
            {
                "nodeid": "other_test.py::test_other",
                "outcome": "passed",
                "duration": 0.15
            },
            {
                "nodeid": "test_async.py::test_async",
                "outcome": "passed",
                "duration": 0.3
            },
            {
                "nodeid": "test_skip.py::test_skip",
                "outcome": "skipped",
                "duration": 0
            }
        ]
    }
    
    result = parse_pytest_json(report)
    
    assert result["success"] is True
    assert result["total"] == 5
    assert result["passed"] == 4
    assert result["failed"] == 0
    assert result["skipped"] == 1
    
    # Check test cases
    assert len(result["test_cases"]) == 5
    
    # Check individual test case structure
    test_case = result["test_cases"][0]
    assert "name" in test_case
    assert "file" in test_case
    assert "outcome" in test_case
    assert "duration" in test_case


def test_parse_pytest_failures():
    """Test parsing pytest results with failures."""
    report = {
        "summary": {
            "total": 3,
            "passed": 1,
            "failed": 2,
            "skipped": 0
        },
        "tests": [
            {
                "nodeid": "test_success.py::test_pass",
                "outcome": "passed",
                "duration": 0.1
            },
            {
                "nodeid": "test_fail.py::test_fail1",
                "outcome": "failed",
                "duration": 0.2,
                "call": {
                    "longrepr": "AssertionError: expected 1 but got 2"
                }
            },
            {
                "nodeid": "test_fail.py::test_fail2",
                "outcome": "failed",
                "duration": 0.15,
                "call": {
                    "longrepr": "TypeError: cannot add str and int"
                }
            }
        ]
    }
    
    result = parse_pytest_json(report)
    
    assert result["success"] is False
    assert result["total"] == 3
    assert result["passed"] == 1
    assert result["failed"] == 2
    assert result["skipped"] == 0
    
    # Check test cases
    assert len(result["test_cases"]) == 3
    
    # Check failed test details
    failed_tests = [t for t in result["test_cases"] if t["outcome"] == "failed"]
    assert len(failed_tests) == 2
    assert "error" in failed_tests[0]
    assert "expected 1 but got 2" in failed_tests[0]["error"]
    assert "cannot add str and int" in failed_tests[1]["error"]


def test_parse_pytest_malformed():
    """Test parsing malformed pytest results."""
    # Missing summary
    report = {"tests": []}
    result = parse_pytest_json(report)
    assert result["success"] is True
    assert result["total"] == 0
    
    # Missing tests
    report = {"summary": {"total": 1, "passed": 1}}
    result = parse_pytest_json(report)
    assert result["success"] is True
    assert result["test_cases"] == []
    
    # Malformed test entry
    report = {
        "summary": {"total": 1, "passed": 1},
        "tests": [{"bad_key": "value"}]
    }
    result = parse_pytest_json(report)
    assert result["success"] is True
    assert len(result["test_cases"]) == 1
    assert result["test_cases"][0]["name"] == "Unknown Test"


def test_parse_pytest_complex_nodeids():
    """Test parsing pytest results with complex node IDs."""
    report = {
        "summary": {
            "total": 3,
            "passed": 3,
            "failed": 0,
            "skipped": 0
        },
        "tests": [
            {
                "nodeid": "tests/unit/test_module.py::TestClass::test_method[param1]",
                "outcome": "passed",
                "duration": 0.1
            },
            {
                "nodeid": "tests/integration/test_feature.py::test_feature[case1-expected1]",
                "outcome": "passed",
                "duration": 0.2
            },
            {
                "nodeid": "tests/functional/test_workflow.py::TestWorkflow::test_step1",
                "outcome": "passed",
                "duration": 0.3
            }
        ]
    }
    
    result = parse_pytest_json(report)
    
    assert result["success"] is True
    assert len(result["test_cases"]) == 3
    
    # Check parsing of complex node IDs
    test_cases = result["test_cases"]
    assert test_cases[0]["file"] == "tests/unit/test_module.py"
    assert test_cases[0]["name"] == "TestClass::test_method[param1]"
    
    assert test_cases[1]["file"] == "tests/integration/test_feature.py"
    assert test_cases[1]["name"] == "test_feature[case1-expected1]"
    
    assert test_cases[2]["file"] == "tests/functional/test_workflow.py"
    assert test_cases[2]["name"] == "TestWorkflow::test_step1"