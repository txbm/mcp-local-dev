# Remaining imports stay the same
import asyncio
import sys
import logging
from typing import Any, Dict, List

from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import stdio
from mcp.types import INTERNAL_ERROR, INVALID_PARAMS

# Rest of the file remains the same as before, with changes only in the main() function

def main() -> None:
    """Simplified main entry point using asyncio directly."""
    asyncio.run(serve_runtime())

if __name__ == "__main__":
    main()