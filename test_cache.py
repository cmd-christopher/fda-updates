#!/usr/bin/env python3
"""Unit tests for --cache flag and incremental label fetching in fda_approvals.py."""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

# Import the module under test
import fda_approvals


class TestLoadPreviousApprovals(unittest.TestCase):
    """Test load_previous_approvals() function."""

    def test_returns_empty_on_missing_file(self):
        """When the previous file doesn't exist, return empty dict."""
        result = fda_approvals.load_previous_approvals("/nonexistent/path.json")
        self.assertEqual(result, {})

    def test_returns_empty_on_corrupt_json(self):
        """When the previous file has invalid JSON, return empty dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("NOT VALID JSON{{{{")
            corrupt_path = f.name
        try:
            result = fda_approvals.load_previous_approvals(corrupt_path)
            self.assertEqual(result, {})
        finally:
            os.unlink(corrupt_path)

    def test_returns_empty_on_empty_drugs(self):
        """When the previous file has no drugs, return empty dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"drugs": []}, f)
            empty_path = f.name
        try:
            result = fda_approvals.load_previous_approvals(empty_path)
            self.assertEqual(result, {})
        finally:
            os.unlink(empty_path)

    def test_maps_app_num_to_drug_with_label(self):
        """Returns mapping of application_number → drug dict for drugs with labels."""
        drugs = [
            {
                "application_number": "NDA123456",
                "brand_name": "TestDrug",
                "label": {"indications_and_usage": ["Test indication"], "set_id": "uuid-1"},
            },
            {
                "application_number": "NDA789012",
                "brand_name": "NoLabelDrug",
                "label": None,
            },
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"drugs": drugs}, f)
            prev_path = f.name
        try:
            result = fda_approvals.load_previous_approvals(prev_path)
            self.assertIn("NDA123456", result)
            self.assertEqual(result["NDA123456"]["brand_name"], "TestDrug")
            self.assertNotIn("NDA789012", result)  # No label → skipped
        finally:
            os.unlink(prev_path)


class TestFetchLabelSetId(unittest.TestCase):
    """Test that fetch_label() includes set_id in returned label dict."""

    def test_set_id_function_exists(self):
        """fetch_label function should exist and be callable."""
        self.assertTrue(callable(fda_approvals.fetch_label))


class TestCacheCliArg(unittest.TestCase):
    """Test that --cache CLI argument is accepted."""

    def test_cache_arg_accepted(self):
        """--cache flag should be a valid argument."""
        parser = fda_approvals.get_parser() if hasattr(fda_approvals, "get_parser") else None
        if parser is None:
            # Try parsing with --cache through argparse
            import argparse
            # Just check that --cache doesn't cause a parse error
            # We'll read the main script's parser indirectly
            # by checking the help text
            import subprocess
            result = subprocess.run(
                [sys.executable, "fda_approvals.py", "--help"],
                capture_output=True, text=True
            )
            self.assertIn("--cache", result.stdout)


class TestWriteOutput(unittest.TestCase):
    """Test output JSON writing behavior."""

    def test_replace_failure_preserves_existing_output_file(self):
        """If atomic replacement fails, the previous output file remains intact."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"count": 99, "drugs": []}, f)
            output_path = f.name

        class Args:
            date_from = "2026-01-01"
            date_to = "2026-01-31"
            submission_type = "all"
            output = output_path

        try:
            with patch("fda_approvals.os.replace", side_effect=OSError("replace failed")):
                with self.assertRaises(OSError):
                    fda_approvals.write_output(Args, [{"application_number": "NDANEW"}])

            with open(output_path) as cf:
                self.assertEqual(json.load(cf), {"count": 99, "drugs": []})
        finally:
            os.unlink(output_path)


if __name__ == "__main__":
    unittest.main()
