#!/usr/bin/env python3
"""Unit tests for the functions in build.py."""

import unittest

# Import the module under test
import build


class TestFormatDate(unittest.TestCase):
    """Test the format_date() function in build.py."""

    def test_valid_dates(self):
        """Test with valid YYYY-MM-DD date strings."""
        self.assertEqual(build.format_date("2023-10-27"), "Oct 27, 2023")
        self.assertEqual(build.format_date("2024-01-05"), "Jan 05, 2024")
        self.assertEqual(build.format_date("1999-12-31"), "Dec 31, 1999")

    def test_empty_and_none(self):
        """Test with empty strings and None."""
        self.assertEqual(build.format_date(""), "")
        self.assertEqual(build.format_date(None), "")

    def test_invalid_date_formats(self):
        """Test with string that are not in YYYY-MM-DD format (should return original value)."""
        self.assertEqual(build.format_date("10-27-2023"), "10-27-2023")
        self.assertEqual(build.format_date("2023/10/27"), "2023/10/27")
        self.assertEqual(build.format_date("not a date"), "not a date")

    def test_invalid_types(self):
        """Test with non-string types (should return original value)."""
        self.assertEqual(build.format_date(12345), 12345)
        self.assertEqual(build.format_date(["2023-10-27"]), ["2023-10-27"])


class TestFormatPiText(unittest.TestCase):
    """Test the format_pi_text() function in build.py."""

    def test_out_of_bounds_placeholders(self):
        """Test that invalid %%TABLE...%% or %%LIST...%% placeholders don't raise IndexError."""
        # This simulates an attacker injecting a large placeholder number
        text = "Some text with %%TABLE999%% and %%LIST888%% in it."
        result = build.format_pi_text(text)

        # The function should ignore invalid placeholders and leave them as is
        self.assertIn("%%TABLE999%%", result)
        self.assertIn("%%LIST888%%", result)

class TestSanitizeHtml(unittest.TestCase):
    """Test the sanitize_html() function in build.py."""

    def test_safe_tags(self):
        """Test that safe tags are preserved."""
        html = '<p class="safe">Hello <b>World</b></p>'
        result = build.sanitize_html(html)
        self.assertEqual(str(result), '<p class="safe">Hello <b>World</b></p>')

    def test_script_removal(self):
        """Test that <script> tags and content are removed."""
        html = '<p>Test</p><script>alert(1)</script>'
        result = build.sanitize_html(html)
        self.assertEqual(str(result), '<p>Test</p>')

    def test_style_attribute_removal(self):
        """Test that style attributes are removed."""
        html = '<p style="color: red;">Red text</p>'
        result = build.sanitize_html(html)
        self.assertEqual(str(result), '<p>Red text</p>')

    def test_event_attribute_removal(self):
        """Test that on* event attributes are removed."""
        html = '<p onclick="alert(1)">Click me</p>'
        result = build.sanitize_html(html)
        self.assertEqual(str(result), '<p>Click me</p>')

    def test_iframe_removal(self):
        """Test that <iframe> tags are removed."""
        html = '<div><iframe src="evil.com"></iframe></div>'
        result = build.sanitize_html(html)
        self.assertEqual(str(result), '<div></div>')

if __name__ == "__main__":
    unittest.main()
