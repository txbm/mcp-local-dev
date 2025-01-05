"""Test fixtures and configuration."""
import pytest
import pytest_asyncio
from pathlib import Path

from mcp_local_dev.sandboxes.sandbox import create_sandbox, cleanup_sandbox

@pytest_asyncio.fixture
async def sandbox():
    """Create a temporary sandbox for testing."""
    sandbox = await create_sandbox("test-")
    try:
        yield sandbox
    finally:
        cleanup_sandbox(sandbox)

@pytest_asyncio.fixture
def fixture_path() -> Path:
    """Get path to test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures_data"
