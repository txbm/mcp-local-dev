"""Tests for statistical functions."""
import pytest
from example.core import mean, median, mode

def test_mean_calculation(sample_numbers):
    """Test mean calculation with known values."""
    assert mean(sample_numbers) == 2.4

def test_mean_empty_sequence(empty_sequence):
    """Test mean raises error for empty sequence."""
    with pytest.raises(ValueError, match="empty sequence"):
        mean(empty_sequence)

def test_median_odd_length(sample_numbers):
    """Test median with odd length sequence."""
    assert median(sample_numbers) == 2.0

def test_median_empty_sequence(empty_sequence):
    """Test median raises error for empty sequence."""
    with pytest.raises(ValueError, match="empty sequence"):
        median(empty_sequence)

def test_mode_calculation(sample_numbers):
    """Test mode finds most common value."""
    assert mode(sample_numbers) == 2.0

def test_mode_multiple_modes(multi_modal_sequence):
    """Test mode raises error when multiple modes exist."""
    with pytest.raises(ValueError, match="Multiple modes"):
        mode(multi_modal_sequence)

def test_mode_empty_sequence(empty_sequence):
    """Test mode raises error for empty sequence."""
    with pytest.raises(ValueError, match="empty sequence"):
        mode(empty_sequence)
