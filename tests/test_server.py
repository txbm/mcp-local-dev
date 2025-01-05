"""Test MCP server implementation."""
import json
import pytest
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import JSONRPCMessage

from mcp_local_dev.server import init_server

@pytest.mark.asyncio 
async def test_server_tool_registration():
    """Test server tool registration via JSON-RPC."""
    server = await init_server()
    
    params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_local_dev.server"]
    )
    
    async with stdio_client(params) as (reader, writer):
        # Send tools/list request
        request = JSONRPCMessage(
            jsonrpc="2.0",
            id=1,
            method="tools/list"
        )
        await writer.send(request)
        
        response = await reader.receive()
        assert isinstance(response, JSONRPCMessage)
        assert "result" in response.model_dump()
        tools = response.result
        
        assert len(tools) > 0
        assert any(t["name"] == "create_environment" for t in tools)
        assert any(t["name"] == "run_tests" for t in tools)
        assert any(t["name"] == "cleanup" for t in tools)

@pytest.mark.asyncio
async def test_server_tool_execution():
    """Test server tool execution via JSON-RPC."""
    params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_local_dev.server"]
    )
    
    async with stdio_client(params) as (reader, writer):
        # Send tools/call request
        request = JSONRPCMessage(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={
                "name": "create_environment",
                "arguments": {
                    "github_url": "https://github.com/txbm/mcp-python-repo-fixture"
                }
            }
        )
        await writer.send(request)
        
        response = await reader.receive()
        assert isinstance(response, JSONRPCMessage)
        assert "result" in response.model_dump()
        result = json.loads(response.result[0]["text"])
        
        assert "id" in result
        assert "working_dir" in result
