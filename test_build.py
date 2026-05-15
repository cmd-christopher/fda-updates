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

    def test_empty_and_none(self):
        """Test with empty strings and None."""
        self.assertEqual(str(build.sanitize_html("")), "")
        self.assertEqual(str(build.sanitize_html(None)), "")

    def test_disallowed_tags_removal(self):
        """Test that disallowed tags are stripped but inner content is preserved if applicable."""
        html = '<p>Test</p><form><input type="text">Submit</form>'
        result = build.sanitize_html(html)
        self.assertEqual(str(result), '<p>Test</p>\nSubmit')

    def test_style_tag_removal(self):
        """Test that <style> tags and their content are removed."""
        html = '<style>body { color: red; }</style><p>Test</p>'
        result = build.sanitize_html(html)
        self.assertEqual(str(result), '<p>Test</p>')

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

from unittest.mock import patch
from datetime import datetime

class TestComputeLastUpdated(unittest.TestCase):
    """Test the compute_last_updated() function in build.py."""

    def test_valid_date_to(self):
        """Test with a valid YYYY-MM-DD date_to format."""
        data = {"query": {"date_to": "2023-10-27"}}
        result = build.compute_last_updated(data)
        self.assertEqual(result, "October 27, 2023")

    @patch('build.datetime')
    def test_invalid_date_format(self, mock_datetime):
        """Test with an invalid date_to format (ValueError)."""
        # We need to preserve strptime to raise ValueError
        mock_datetime.strptime.side_effect = ValueError
        # Mock now() to return a fixed datetime for predictability
        fixed_now = datetime(2024, 1, 5)
        mock_datetime.now.return_value = fixed_now

        data = {"query": {"date_to": "invalid-date"}}
        result = build.compute_last_updated(data)
        self.assertEqual(result, "January 05, 2024")

    @patch('build.datetime')
    def test_invalid_date_type(self, mock_datetime):
        """Test with an invalid date_to type (TypeError)."""
        mock_datetime.strptime.side_effect = TypeError
        fixed_now = datetime(2024, 1, 5)
        mock_datetime.now.return_value = fixed_now

        data = {"query": {"date_to": 12345}}
        result = build.compute_last_updated(data)
        self.assertEqual(result, "January 05, 2024")

    @patch('os.path.getmtime')
    def test_missing_date_to(self, mock_getmtime):
        """Test missing date_to which falls back to file modification time."""
        # 1704412800 is 2024-01-05 00:00:00 UTC (or local equivalent)
        # Let's mock a specific timestamp
        test_timestamp = 1704412800
        mock_getmtime.return_value = test_timestamp

        data = {"query": {}}
        result = build.compute_last_updated(data)

        expected_date = datetime.fromtimestamp(test_timestamp).strftime("%B %d, %Y")
        self.assertEqual(result, expected_date)

class TestStyleXrefsInBody(unittest.TestCase):
    """Test the _style_xrefs_in_body() function in build.py."""

    def test_bracketed_references(self):
        """Test [see ...] references containing numbers in parentheses."""
        text = "This is a test [see Warnings and Precautions (5.1)]."
        expected = 'This is a test [see Warnings and Precautions <span class="xref">5.1</span>].'
        self.assertEqual(build._style_xrefs_in_body(text), expected)

        text = "[see Dosage (2)]"
        expected = '[see Dosage <span class="xref">2</span>]'
        self.assertEqual(build._style_xrefs_in_body(text), expected)

        # Case-insensitive "see"
        text = "[SEE WARNINGS (5.1)]"
        expected = '[SEE WARNINGS <span class="xref">5.1</span>]'
        self.assertEqual(build._style_xrefs_in_body(text), expected)

    def test_standalone_parentheses(self):
        """Test standalone numbers in parentheses."""
        text = "Side effects include nausea (6.1)."
        expected = 'Side effects include nausea <span class="xref">(6.1)</span>.'
        self.assertEqual(build._style_xrefs_in_body(text), expected)

        text = "Dose: 10 mg (2)."
        expected = 'Dose: 10 mg <span class="xref">(2)</span>.'
        self.assertEqual(build._style_xrefs_in_body(text), expected)

    def test_multiple_numbers(self):
        """Test multiple numbers inside parentheses."""
        text = "[see Warnings (5.1, 5.2)]"
        expected = '[see Warnings <span class="xref">5.1, 5.2</span>]'
        self.assertEqual(build._style_xrefs_in_body(text), expected)

        text = "See section (6.1, 6.2)."
        expected = 'See section <span class="xref">(6.1, 6.2)</span>.'
        self.assertEqual(build._style_xrefs_in_body(text), expected)

        text = "[see Info (1, 2.1, 3)]"
        expected = '[see Info <span class="xref">1, 2.1, 3</span>]'
        self.assertEqual(build._style_xrefs_in_body(text), expected)

    def test_negative_cases(self):
        """Test cases that should not be styled."""
        text = "(not a number)"
        self.assertEqual(build._style_xrefs_in_body(text), text)

        text = "()"
        self.assertEqual(build._style_xrefs_in_body(text), text)

        text = "[see Details (N/A)]"
        self.assertEqual(build._style_xrefs_in_body(text), text)

    def test_mixed_cases(self):
        """Test a mix of styled and unstyled parentheses."""
        text = "Call (555) 123-4567 [see Contact (8.1)] or visit (website)."
        # Note: The current implementation of _style_xrefs_in_body wraps ANY standalone integer or float in parentheses.
        # Thus, (555) becomes <span class="xref">(555)</span>. This behavior might be unintentional but we assert the current behavior.
        expected = 'Call <span class="xref">(555)</span> 123-4567 [see Contact <span class="xref">8.1</span>] or visit (website).'
        self.assertEqual(build._style_xrefs_in_body(text), expected)

if __name__ == "__main__":
    unittest.main()
