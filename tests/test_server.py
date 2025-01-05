"""Test MCP server implementation."""
import anyio
import json
import pytest
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any
import asyncio

from mcp.types import JSONRPCMessage, JSONRPCRequest, JSONRPCResponse, Tool
from mcp.server.models import InitializationOptions
from mcp.types import ServerCapabilities, ToolsCapability, LoggingCapability

from mcp_local_dev.server import init_server

@asynccontextmanager
async def create_test_streams() -> AsyncGenerator[tuple[anyio.abc.ObjectSendStream, 
                                                      anyio.abc.ObjectReceiveStream,
                                                      anyio.abc.ObjectSendStream,
                                                      anyio.abc.ObjectReceiveStream], None]:
    """Create bidirectional streams for testing."""
    client_to_server_send, client_to_server_receive = anyio.create_memory_object_stream(100)
    server_to_client_send, server_to_client_receive = anyio.create_memory_object_stream(100)
    
    try:
        yield client_to_server_send, server_to_client_receive, server_to_client_send, client_to_server_receive
    finally:
        # Only close after all operations are complete
        async with anyio.create_task_group() as tg:
            async def close_stream(stream):
                await stream.aclose()
            tg.start_soon(close_stream, client_to_server_send)
            tg.start_soon(close_stream, client_to_server_receive) 
            tg.start_soon(close_stream, server_to_client_send)
            tg.start_soon(close_stream, server_to_client_receive)

async def send_request(send_stream: anyio.abc.ObjectSendStream,
                      method: str,
                      params: Dict[str, Any] | None = None,
                      request_id: int = 1) -> None:
    """Send a JSON-RPC request."""
    if method == "initialize":
        # Add required fields for initialization
        params = {
            "protocolVersion": "1.0",
            "capabilities": {
                "tools": {"listChanged": False},
                "logging": {}
            },
            "clientInfo": params.get("clientInfo", {}) if params else {}
        }
    
    request = JSONRPCMessage(
        root=JSONRPCRequest(
            jsonrpc="2.0",
            id=request_id,
            method=method,
            params=params or {}
        )
    )
    await send_stream.send(request)

async def receive_response(receive_stream: anyio.abc.ObjectReceiveStream, 
                         timeout: float = 2.0) -> Dict[str, Any]:
    """Receive and validate JSON-RPC response with timeout."""
    with anyio.move_on_after(timeout) as scope:
        response = await receive_stream.receive()
        assert isinstance(response.root, JSONRPCResponse)
        return response.root.result
        
    if scope.cancel_called:
        raise RuntimeError(f"No response received within {timeout} seconds")

@pytest.mark.asyncio 
async def test_server_initialization():
    """Test server initialization and capabilities."""
    async with create_test_streams() as (client_send, server_receive, server_send, client_receive):
        async with anyio.create_task_group() as tg:
            server = await init_server()
            
            async def run_server():
                try:
                    await server.run(
                        client_receive,
                        server_send,
                        InitializationOptions(
                            server_name="test-server",
                            server_version="0.1.0",
                            capabilities=ServerCapabilities(
                                tools=ToolsCapability(listChanged=False),
                                logging=LoggingCapability()
                            )
                        )
                    )
                except anyio.get_cancelled_exc_class():
                    pass  # Expected when we cancel the task
            
            tg.start_soon(run_server)
            
            try:
                # Send initialization request first
                await send_request(
                    client_send,
                    "initialize",
                    {
                        "clientInfo": {
                            "name": "test-client",
                            "version": "0.1.0"
                        }
                    }
                )

                # Wait for initialization response
                init_response = await receive_response(server_receive)
                assert init_response["status"] == "success"

                # Test tools listing
                await send_request(client_send, "tools/list")
                tools_response = await receive_response(server_receive)
                
                assert isinstance(tools_response, list)
                assert all(isinstance(tool, dict) for tool in tools_response)
                assert any(t["name"] == "create_environment" for t in tools_response)
                assert any(t["name"] == "run_tests" for t in tools_response)
                assert any(t["name"] == "cleanup" for t in tools_response)
            finally:
                # Ensure server task is cancelled
                tg.cancel_scope.cancel()

@pytest.mark.asyncio
async def test_tool_execution():
    """Test tool execution with proper protocol flow."""
    async with create_test_streams() as (client_send, server_receive, server_send, client_receive):
        async with anyio.create_task_group() as tg:
            server = await init_server()
            
            async def run_server():
                try:
                    await server.run(
                        client_receive,
                        server_send,
                        InitializationOptions(
                            server_name="test-server",
                            server_version="0.1.0",
                            capabilities=ServerCapabilities(
                                tools=ToolsCapability(listChanged=False),
                                logging=LoggingCapability()
                            )
                        )
                    )
                except anyio.get_cancelled_exc_class():
                    pass
            
            tg.start_soon(run_server)
            
            try:
                # Send initialization request first
                await send_request(
                    client_send,
                    "initialize",
                    {
                        "clientInfo": {
                            "name": "test-client",
                            "version": "0.1.0"
                        }
                    }
                )

                # Wait for initialization response
                init_response = await receive_response(server_receive)
                assert init_response["status"] == "success"

                # Test tool execution
                await send_request(
                    client_send,
                    "tools/call",
                    {
                        "name": "create_environment",
                        "arguments": {
                            "github_url": "https://github.com/txbm/mcp-python-repo-fixture"
                        }
                    }
                )
                
                tool_response = await receive_response(server_receive)
                assert isinstance(tool_response, list)
                assert len(tool_response) == 1
                assert tool_response[0]["type"] == "text"
                
                result = json.loads(tool_response[0]["text"])
                assert "id" in result
                assert "working_dir" in result
                assert "runtime" in result
            finally:
                tg.cancel_scope.cancel()

@pytest.mark.asyncio
async def test_error_handling():
    """Test server error handling."""
    async with create_test_streams() as (client_send, server_receive, server_send, client_receive):
        async with anyio.create_task_group() as tg:
            server = await init_server()
            
            async def run_server():
                try:
                    await server.run(
                        client_receive,
                        server_send,
                        InitializationOptions(
                            server_name="test-server",
                            server_version="0.1.0",
                            capabilities=ServerCapabilities(
                                tools=ToolsCapability(listChanged=False),
                                logging=LoggingCapability()
                            )
                        )
                    )
                except anyio.get_cancelled_exc_class():
                    pass
            
            tg.start_soon(run_server)
            
            try:
                # Send initialization request first
                await send_request(
                    client_send,
                    "initialize",
                    {
                        "clientInfo": {
                            "name": "test-client",
                            "version": "0.1.0"
                        }
                    }
                )

                # Wait for initialization response
                init_response = await receive_response(server_receive)
                assert init_response["status"] == "success"

                # Test invalid tool name
                await send_request(
                    client_send,
                    "tools/call",
                    {
                        "name": "nonexistent_tool",
                        "arguments": {}
                    }
                )
                
                error_response = await receive_response(server_receive)
                assert isinstance(error_response.root, JSONRPCResponse)
                assert error_response.root.error is not None
            finally:
                tg.cancel_scope.cancel()
