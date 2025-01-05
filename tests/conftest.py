"""Test fixtures and configuration."""
import pytest
import pytest_asyncio
from pathlib import Path

@pytest_asyncio.fixture
def fixture_path() -> Path:
    """Get path to test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures_data"
