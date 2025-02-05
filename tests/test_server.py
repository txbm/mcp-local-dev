"""Test MCP server implementation."""
import anyio
import json
import pytest
from mcp_local_dev.logging import get_logger

logger = get_logger(__name__)
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any
import asyncio

from mcp.types import JSONRPCMessage, JSONRPCRequest, JSONRPCResponse, JSONRPCNotification, Tool
from mcp.server.models import InitializationOptions
from mcp.types import ServerCapabilities, ToolsCapability, LoggingCapability

from mcp_local_dev.server import init_server

@asynccontextmanager
async def create_test_streams() -> AsyncGenerator[tuple[anyio.abc.ObjectSendStream, 
                                                      anyio.abc.ObjectReceiveStream,
                                                      anyio.abc.ObjectSendStream,
                                                      anyio.abc.ObjectReceiveStream], None]:
    """Create bidirectional streams for testing.
    Returns (client_send, server_receive, server_send, client_receive)
    """
    # Create two separate memory streams for bidirectional communication
    client_send, server_receive = anyio.create_memory_object_stream(100)  # Client -> Server
    server_send, client_receive = anyio.create_memory_object_stream(100)  # Server -> Client
    
    try:
        # Return the streams in the correct order:
        # client_send -> server_receive -> server processes -> server_send -> client_receive
        yield client_send, server_receive, server_send, client_receive
    finally:
        async with anyio.create_task_group() as tg:
            async def close_stream(stream):
                await stream.aclose()
            tg.start_soon(close_stream, client_send)
            tg.start_soon(close_stream, server_receive)
            tg.start_soon(close_stream, server_send)
            tg.start_soon(close_stream, client_receive)

async def send_request(send_stream: anyio.abc.ObjectSendStream,
                      method: str,
                      params: Dict[str, Any] | None = None,
                      request_id: int | None = 1) -> None:
    """Send a JSON-RPC request or notification."""
    match method:
        case "initialize":
            # Special case: initialize request needs specific params
            message = JSONRPCMessage(
                root=JSONRPCRequest(
                    jsonrpc="2.0",
                    id=request_id,
                    method=method,
                    params={
                        "protocolVersion": "1.0",
                        "capabilities": {
                            "tools": {"listChanged": False},
                            "logging": {}
                        },
                        "clientInfo": params.get("clientInfo", {}) if params else {}
                    }
                )
            )
        case "initialized":
            # Special case: initialized is a notification with specific method name
            message = JSONRPCMessage(
                root=JSONRPCNotification(
                    jsonrpc="2.0",
                    method="notifications/initialized",
                    params=params or {}
                )
            )
        case _:
            # Default case: regular request
            message = JSONRPCMessage(
                root=JSONRPCRequest(
                    jsonrpc="2.0",
                    id=request_id,
                    method=method,
                    params=params or {}
                )
            )
    
    await send_stream.send(message)

async def receive_response(receive_stream: anyio.abc.ObjectReceiveStream, 
                         timeout: float = 5.0) -> Dict[str, Any]:
    """Receive and validate JSON-RPC response with timeout."""
    with anyio.move_on_after(timeout) as scope:
        response = await receive_stream.receive()
        assert isinstance(response.root, JSONRPCResponse)
        result = response.root.result
        
        # Special case for tools listing
        if isinstance(result, dict) and 'tools' in result:
            return result['tools']
            
        return result
        
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
                        server_receive,
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

            # Start server task
            tg.start_soon(run_server)

            # Send initialize request with proper protocol version
            await send_request(
                client_send,
                "initialize",
                {
                    "protocolVersion": "1.0",
                    "clientInfo": {
                        "name": "test-client",
                        "version": "0.1.0"
                    },
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "logging": {}
                    }
                }
            )

            # Wait for initialization response
            init_response = await receive_response(client_receive)
            assert "serverInfo" in init_response
            assert "name" in init_response["serverInfo"]
            assert "version" in init_response["serverInfo"]
            assert "capabilities" in init_response

            # Send initialized notification without request id
            await send_request(client_send, "initialized", None, None)

            # Now test tools listing
            await send_request(client_send, "tools/list")
            tools_response = await receive_response(client_receive)
            
            assert isinstance(tools_response, list)
            assert all(isinstance(tool, dict) for tool in tools_response)
            assert any(t["name"] == "local_dev_from_github" for t in tools_response)
            assert any(t["name"] == "local_dev_from_filesystem" for t in tools_response)
            assert any(t["name"] == "local_dev_run_tests" for t in tools_response)
            assert any(t["name"] == "local_dev_cleanup" for t in tools_response)

            # Clean up
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
                        server_receive,
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

            # Initialize properly
            await send_request(
                client_send,
                "initialize",
                {
                    "protocolVersion": "1.0",
                    "clientInfo": {
                        "name": "test-client",
                        "version": "0.1.0"
                    },
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "logging": {}
                    }
                }
            )

            init_response = await receive_response(client_receive)
            assert "serverInfo" in init_response
            
            # Send initialized notification without request id
            await send_request(client_send, "initialized", None, None)

            # Now test tool execution
            await send_request(
                client_send,
                "tools/call",
                {
                    "name": "local_dev_from_github",
                    "arguments": {
                        "github_url": "https://github.com/txbm/mcp-python-repo-fixture"
                    }
                }
            )
            logger.debug("Tool request sent, waiting for response")
            
            tool_response = await receive_response(client_receive)
            assert isinstance(tool_response["content"], list)
            assert len(tool_response["content"]) == 1
            assert tool_response["content"][0]["type"] == "text"
            
            result = json.loads(tool_response["content"][0]["text"])
            logger.debug("Tool execution result", extra={"data": result})
            
            if not result["success"]:
                logger.debug("Tool execution failed", extra={"error": result.get('error')})
                
            assert result["success"] is True, f"Tool execution failed: {result.get('error')}"  # Add error message to assertion
            assert "data" in result
            assert "id" in result["data"]
            assert "working_dir" in result["data"]
            assert "runtime" in result["data"]

            # Clean up
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
                        server_receive,
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

            # Initialize properly
            await send_request(
                client_send,
                "initialize",
                {
                    "protocolVersion": "1.0",
                    "clientInfo": {
                        "name": "test-client",
                        "version": "0.1.0"
                    },
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "logging": {}
                    }
                }
            )

            init_response = await receive_response(client_receive)
            assert "serverInfo" in init_response
            
            # Send initialized notification without request id
            await send_request(client_send, "initialized", None, None)

            # Now test invalid tool name
            await send_request(
                client_send,
                "tools/call",
                {
                    "name": "invalid_tool_name",
                    "arguments": {}
                }
            )
            
            tool_response = await receive_response(client_receive)
            assert isinstance(tool_response["content"], list)
            assert len(tool_response["content"]) == 1
            assert tool_response["content"][0]["type"] == "text"
            
            result = json.loads(tool_response["content"][0]["text"])
            assert result["success"] is False
            assert "error" in result
            assert "Unknown tool" in result["error"]

            # Clean up
            tg.cancel_scope.cancel()
