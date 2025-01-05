"""Test MCP server implementation."""
import json
import asyncio
import pytest
from mcp.server import stdio
from mcp.server.models import InitializationOptions
from mcp.types import ServerCapabilities, ToolsCapability, LoggingCapability

from mcp_local_dev.server import init_server

async def send_request(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, method: str, params: dict = None) -> dict:
    """Send JSON-RPC request to server and get response."""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {}
    }
    
    writer.write(json.dumps(request).encode() + b"\n")
    await writer.drain()
    
    response = await reader.readline()
    return json.loads(response.decode())

@pytest.mark.asyncio 
async def test_server_tool_registration():
    """Test server tool registration via JSON-RPC."""
    server = await init_server()
    
    async with stdio.stdio_server() as (reader, writer):
        # Initialize server
        init_options = InitializationOptions(
            server_name="mcp-local-dev",
            server_version="0.1.0",
            capabilities=ServerCapabilities(
                tools=ToolsCapability(listChanged=False),
                logging=LoggingCapability(),
            )
        )
        
        # Start server in background task
        server_task = asyncio.create_task(
            server.run(reader, writer, init_options)
        )
        
        try:
            # Send tools/list request
            response = await send_request(reader, writer, "tools/list")
            
            assert "result" in response
            tools = response["result"]
            assert len(tools) > 0
            assert any(t["name"] == "create_environment" for t in tools)
            assert any(t["name"] == "run_tests" for t in tools)
            assert any(t["name"] == "cleanup" for t in tools)
        finally:
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

@pytest.mark.asyncio
async def test_server_tool_execution():
    """Test server tool execution via JSON-RPC."""
    server = await init_server()
    
    async with stdio.stdio_server() as (reader, writer):
        init_options = InitializationOptions(
            server_name="mcp-local-dev",
            server_version="0.1.0",
            capabilities=ServerCapabilities(
                tools=ToolsCapability(listChanged=False),
                logging=LoggingCapability(),
            )
        )
        
        server_task = asyncio.create_task(
            server.run(reader, writer, init_options)
        )
        
        try:
            # Send tools/call request
            response = await send_request(
                reader, 
                writer,
                "tools/call",
                {
                    "name": "create_environment",
                    "arguments": {
                        "github_url": "https://github.com/txbm/mcp-python-repo-fixture"
                    }
                }
            )
            
            assert "result" in response
            result = json.loads(response["result"][0]["text"])
            assert "id" in result
            assert "working_dir" in result
        finally:
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
