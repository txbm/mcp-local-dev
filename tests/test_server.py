"""Test MCP server implementation."""
import json
import pytest
import mcp.types as types
from mcp_local_dev.server import init_server

@pytest.mark.asyncio
async def test_server_tool_registration():
    """Test server tool registration"""
    server = await init_server()
    
    # Use list_tools() instead of handle_list_tools_request
    tools = await server.list_tools()
    
    assert len(tools) > 0
    assert any(t.name == "create_environment" for t in tools)
    assert any(t.name == "run_tests" for t in tools)
    assert any(t.name == "cleanup" for t in tools)

@pytest.mark.asyncio
async def test_server_tool_execution():
    """Test server tool execution"""
    server = await init_server()
    
    # Use call_tool() instead of handle_call_tool_request_internal
    result = await server.call_tool(
        "create_environment",
        {
            "github_url": "https://github.com/txbm/mcp-python-repo-fixture"
        }
    )
    
    assert len(result) == 1
    assert result[0].type == "text"
    data = json.loads(result[0].text)
    assert "id" in data
    assert "working_dir" in data
