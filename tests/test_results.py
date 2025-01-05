import json
import pytest
from mcp_local_dev.test_runners.results import parse_pytest_json, format_test_results
from mcp.types import TextContent

def test_parse_pytest_json():
    """Test parsing pytest JSON output"""
    sample_output = {
        "stdout": "test_sample.py::test_basic PASSED",
        "stderr": "",
        "returncode": 0
    }
    
    result = parse_pytest_json(sample_output)
    assert result["success"] is True
    assert result["summary"]["total"] == 1
    assert result["summary"]["passed"] == 1
    assert len(result["tests"]) == 1
    assert result["tests"][0]["outcome"] == "passed"

def test_parse_pytest_json_invalid():
    """Test parsing invalid pytest output"""
    with pytest.raises(ValueError):
        parse_pytest_json("invalid")

def test_format_test_results():
    """Test formatting test results for MCP"""
    test_data = {
        "success": True,
        "framework": "pytest",
        "summary": {"total": 1, "passed": 1},
        "tests": [{"nodeid": "test_basic", "outcome": "passed"}]
    }
    
    results = format_test_results("pytest", test_data)
    assert len(results) == 1
    assert results[0].type == "text"
    
    data = json.loads(results[0].text)
    assert data["success"] is True
    assert data["runner"] == "pytest"
    assert len(data["test_cases"]) == 1
