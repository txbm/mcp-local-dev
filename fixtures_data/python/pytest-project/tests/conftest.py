"""Test fixtures."""
import pytest
from typing import List

@pytest.fixture
def sample_numbers() -> List[float]:
    """Sample sequence with known statistics."""
    return [1.0, 2.0, 2.0, 3.0, 4.0]

@pytest.fixture
def empty_sequence() -> List[float]:
    """Empty sequence for testing error cases."""
    return []

@pytest.fixture
def multi_modal_sequence() -> List[float]:
    """Sequence with multiple modes."""
    return [1.0, 1.0, 2.0, 2.0, 3.0]
