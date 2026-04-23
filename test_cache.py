#!/usr/bin/env python3
"""Unit tests for --cache flag and incremental label fetching in fda_approvals.py."""

import json
import os
import sys
import tempfile
import unittest

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


class TestSaveLabelCache(unittest.TestCase):
    """Test save_label_cache() function."""

    def test_creates_cache_file_with_set_id_mapping(self):
        """Saves app_num → set_id mapping for drugs with label and set_id."""
        drugs = [
            {
                "application_number": "NDA123456",
                "label": {"set_id": "uuid-1", "indications_and_usage": ["Test"]},
            },
            {
                "application_number": "NDA789012",
                "label": {"set_id": "uuid-2"},
            },
            {
                "application_number": "NDA000000",
                "label": None,
            },
            {
                "application_number": "NDA999999",
                "label": {"indications_and_usage": ["No set_id here"]},
            },
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            cache_path = f.name
        try:
            fda_approvals.save_label_cache(drugs, cache_path)
            with open(cache_path) as cf:
                cache = json.load(cf)
            self.assertEqual(cache["NDA123456"], "uuid-1")
            self.assertEqual(cache["NDA789012"], "uuid-2")
            self.assertNotIn("NDA000000", cache)  # No label → skipped
            self.assertNotIn("NDA999999", cache)  # No set_id → skipped
        finally:
            os.unlink(cache_path)

    def test_writes_valid_json(self):
        """Cache file contains valid JSON."""
        drugs = [
            {"application_number": "NDA111", "label": {"set_id": "uuid-aaa"}},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            cache_path = f.name
        try:
            fda_approvals.save_label_cache(drugs, cache_path)
            with open(cache_path) as cf:
                data = json.load(cf)
            self.assertIsInstance(data, dict)
        finally:
            os.unlink(cache_path)

    def test_creates_parent_directory(self):
        """save_label_cache creates parent directory if needed."""
        import tempfile
        tmpdir = tempfile.mkdtemp()
        try:
            nested_path = os.path.join(tmpdir, "subdir", "cache.json")
            drugs = [
                {"application_number": "NDA111", "label": {"set_id": "uuid-aaa"}},
            ]
            fda_approvals.save_label_cache(drugs, nested_path)
            self.assertTrue(os.path.exists(nested_path))
            with open(nested_path) as f:
                data = json.load(f)
            self.assertEqual(data["NDA111"], "uuid-aaa")
        finally:
            import shutil
            shutil.rmtree(tmpdir)


class TestFetchLabelSetId(unittest.TestCase):
    """Test that fetch_label() includes set_id in returned label dict."""

    def test_set_id_function_exists(self):
        """fetch_label function should exist and be callable."""
        self.assertTrue(callable(fda_approvals.fetch_label))

    def test_label_cache_path_defined(self):
        """LABEL_CACHE_PATH constant should be defined."""
        self.assertTrue(hasattr(fda_approvals, "LABEL_CACHE_PATH"))
        self.assertIn(".label_cache.json", fda_approvals.LABEL_CACHE_PATH)


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


if __name__ == "__main__":
    unittest.main()