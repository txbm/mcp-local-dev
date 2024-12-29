# MCP Runtime Server

A Model Context Protocol server for managing secure runtime environments and capturing program execution.

## Installation

The MCP Runtime Server requires Python 3.9 or higher and depends on the MCP SDK package.

1. First, install the MCP SDK:
```bash
pip install mcp>=0.7.0
```

2. Then install the runtime server:
```bash
pip install mcp-runtime-server
```

For development installation:

```bash
# Install MCP SDK first
pip install mcp>=0.7.0

# Install in development mode
pip install -e .
```

### Extra Features

For enhanced security features on Linux, install with:
```bash
pip install mcp-runtime-server[linux]
```

This includes:
- Python seccomp for syscall filtering
- Python unshare for namespace isolation

For development tools:
```bash
pip install mcp-runtime-server[dev]
```

## Usage

The runtime server provides several tools for managing isolated runtime environments:

```python
from mcp_runtime_server import RuntimeServer
from mcp_runtime_server.types import RuntimeConfig, RuntimeManager

# Create and start the server
server = RuntimeServer()
await server.serve()
```

### Available Tools

1. **create_environment**: Create a new runtime environment with sandbox isolation
2. **run_command**: Run a command in an isolated sandbox environment
3. **auto_run_tests**: Auto-detect and run tests in a sandboxed environment
4. **cleanup_environment**: Clean up a sandboxed environment

## Development

1. Install development dependencies:
```bash
pip install -e .[dev]
```

2. Run tests:
```bash
pytest
```

3. Format code:
```bash
black .
```

4. Run type checks:
```bash
mypy .
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

[MIT License](LICENSE)
