import json
import pytest
import asyncio
import mcp.types as types
from mcp_local_dev.server import init_server

@pytest.mark.asyncio 
async def test_server_tool_registration():
    """Test server tool registration"""
    server = await init_server()
    tools = server.list_tools()  # Property, no await needed
    
    assert len(tools) > 0
    assert any(t.name == "create_environment" for t in tools)
    assert any(t.name == "run_tests" for t in tools)
    assert any(t.name == "cleanup" for t in tools)

@pytest.mark.asyncio
async def test_server_tool_execution():
    """Test server tool execution"""
    server = await init_server()
    
    request = types.CallToolRequest(
        method="create_environment",
        params={"github_url": "https://github.com/txbm/mcp-python-repo-fixture"}
    )
    
    result = await server.call_tool(request)
    
    assert len(result) == 1
    assert result[0].type == "text"
    data = json.loads(result[0].text)
    assert "id" in data
    assert "working_dir" in data
