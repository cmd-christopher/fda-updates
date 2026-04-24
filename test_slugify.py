#!/usr/bin/env python3
"""Unit tests for the slugify function in fda_approvals.py."""

import unittest

# Import the module under test
import fda_approvals

class TestSlugify(unittest.TestCase):
    """Test the slugify() function."""

    def test_empty_and_none(self):
        """Test with empty string and None."""
        self.assertEqual(fda_approvals.slugify(""), "")
        self.assertEqual(fda_approvals.slugify(None), "")

    def test_normal_string(self):
        """Test with normal alphanumeric strings."""
        self.assertEqual(fda_approvals.slugify("Aspirin"), "aspirin")
        self.assertEqual(fda_approvals.slugify("Tylenol PM"), "tylenol-pm")

    def test_special_characters(self):
        """Test with special characters."""
        self.assertEqual(fda_approvals.slugify("Vitamin C (Ascorbic Acid)"), "vitamin-c-ascorbic-acid")
        self.assertEqual(fda_approvals.slugify("CoQ-10 @ 100mg!"), "coq-10-100mg")
        self.assertEqual(fda_approvals.slugify("Pain-Relief, Extra Strength."), "pain-relief-extra-strength")

    def test_diacritics_and_accents(self):
        """Test with diacritics and accents (unicode normalization)."""
        self.assertEqual(fda_approvals.slugify("Crème Brûlée"), "creme-brulee")
        self.assertEqual(fda_approvals.slugify("Zürich"), "zurich")
        self.assertEqual(fda_approvals.slugify("El Niño"), "el-nino")

    def test_multiple_spaces_and_dashes(self):
        """Test with multiple spaces and dashes."""
        self.assertEqual(fda_approvals.slugify("Super   Duper---Drug"), "super-duper-drug")
        self.assertEqual(fda_approvals.slugify("   A   B   "), "a-b")
        self.assertEqual(fda_approvals.slugify("---C---D---"), "c-d")

    def test_leading_trailing_spaces_and_dashes(self):
        """Test with leading and trailing spaces and dashes."""
        self.assertEqual(fda_approvals.slugify("  Hello World  "), "hello-world")
        self.assertEqual(fda_approvals.slugify("-Hello-World-"), "hello-world")
        self.assertEqual(fda_approvals.slugify(" - Hello World - "), "hello-world")

    def test_numbers(self):
        """Test with numbers."""
        self.assertEqual(fda_approvals.slugify("Formula 409"), "formula-409")
        self.assertEqual(fda_approvals.slugify("12345"), "12345")

if __name__ == "__main__":
    unittest.main()
