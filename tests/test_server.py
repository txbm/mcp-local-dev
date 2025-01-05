import json
import pytest
import mcp.types as types
from mcp_local_dev.server import init_server

@pytest.mark.asyncio 
async def test_server_tool_registration():
    """Test server tool registration"""
    server = await init_server()
    
    # ListToolsRequest requires method="tools/list"
    request = types.ListToolsRequest(method="tools/list")
    tools = await server.handle_list_tools_request(request)
    
    assert len(tools) > 0
    assert any(t.name == "create_environment" for t in tools)
    assert any(t.name == "run_tests" for t in tools)
    assert any(t.name == "cleanup" for t in tools)

@pytest.mark.asyncio
async def test_server_tool_execution():
    """Test server tool execution"""
    server = await init_server()
    
    # Create request with correct structure
    request = types.CallToolRequest(
        method="tools/call",
        params={
            "name": "create_environment",
            "arguments": {
                "github_url": "https://github.com/txbm/mcp-python-repo-fixture"
            }
        }
    )
    
    # Use handle_call_tool_request_internal instead of handle_call_tool_request
    result = await server.handle_call_tool_request_internal(request)
    
    assert len(result) == 1
    assert result[0].type == "text"
    data = json.loads(result[0].text)
    assert "id" in data
    assert "working_dir" in data
