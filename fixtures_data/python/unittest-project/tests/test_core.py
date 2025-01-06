"""Tests for statistical functions."""
import unittest
from example.core import mean, median, mode

class TestStatisticalFunctions(unittest.TestCase):
    """Test cases for statistical functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_numbers = [1.0, 2.0, 2.0, 3.0, 4.0]
        self.empty_sequence = []
        self.multi_modal_sequence = [1.0, 1.0, 2.0, 2.0, 3.0]

    def test_mean_calculation(self):
        """Test mean calculation with known values."""
        self.assertEqual(mean(self.sample_numbers), 2.4)

    def test_mean_empty_sequence(self):
        """Test mean raises error for empty sequence."""
        with self.assertRaisesRegex(ValueError, "empty sequence"):
            mean(self.empty_sequence)

    def test_median_odd_length(self):
        """Test median with odd length sequence."""
        self.assertEqual(median(self.sample_numbers), 2.0)

    def test_median_empty_sequence(self):
        """Test median raises error for empty sequence."""
        with self.assertRaisesRegex(ValueError, "empty sequence"):
            median(self.empty_sequence)

    def test_mode_calculation(self):
        """Test mode finds most common value."""
        self.assertEqual(mode(self.sample_numbers), 2.0)

    def test_mode_multiple_modes(self):
        """Test mode raises error when multiple modes exist."""
        with self.assertRaisesRegex(ValueError, "Multiple modes"):
            mode(self.multi_modal_sequence)

    def test_mode_empty_sequence(self):
        """Test mode raises error for empty sequence."""
        with self.assertRaisesRegex(ValueError, "empty sequence"):
            mode(self.empty_sequence)

if __name__ == '__main__':
    unittest.main()
