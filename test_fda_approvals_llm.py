import json
import unittest
from unittest.mock import MagicMock, patch
import fda_approvals

class TestSummarizeIndicationsBatch(unittest.TestCase):
    @patch('fda_approvals.urlopen')
    @patch('fda_approvals.time.sleep')
    def test_summarize_indications_batch_exception_fallback(self, mock_sleep, mock_urlopen):
        """Test fallback behavior when API call raises an exception."""
        # Setup mock to raise Exception to hit the except Exception block
        mock_urlopen.side_effect = Exception("Mocked API Error")

        # Input data with multiple drugs including brand_name and generic_name
        drugs = [
            {
                "application_number": "NDA123",
                "brand_name": "TestBrand",
                "generic_name": "TestGeneric",
                "label": {
                    "indications_and_usage": ["Treats disease A"]
                }
            },
            {
                "application_number": "NDA456",
                "brand_name": "", # No brand name to test generic_name fallback
                "generic_name": "GenericBrand",
                "label": {
                    "indications_and_usage": ["Treats disease B"]
                }
            }
        ]

        # Initial state
        summaries_cache = {}
        # Run function
        fda_approvals.summarize_indications_batch(drugs, summaries_cache)

        # Fallbacks are shown but not cached, so the next run retries them.
        self.assertEqual(summaries_cache, {})
        self.assertEqual(drugs[0]["indication_summary"], "TestBrand")
        self.assertEqual(drugs[1]["indication_summary"], "GenericBrand")


def _ollama_reply(content):
    resp = MagicMock()
    resp.read.return_value = json.dumps({"message": {"content": content}}).encode()
    cm = MagicMock()
    cm.__enter__.return_value = resp
    return cm


def _drug(app="NDA221276", brand="HIBSAGO"):
    return {
        "application_number": app,
        "brand_name": brand,
        "generic_name": "",
        "label": {"indications_and_usage": ["treatment of chronic hepatitis B virus infection"]},
    }


class TestSummarizeReplies(unittest.TestCase):
    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_literal_cache_key_reply_is_accepted(self, mock_urlopen, mock_sleep):
        """The model often writes the literal CACHE_KEY instead of the real key."""
        mock_urlopen.return_value = _ollama_reply("CACHE_KEY|chronic hepatitis B virus infection")
        drug = _drug()
        cache = {}
        result = fda_approvals.summarize_indications_batch([drug], cache)
        key = fda_approvals.indication_cache_key(drug)
        self.assertEqual(result, (1, 0))
        self.assertEqual(cache[key], "chronic hepatitis B virus infection")
        self.assertEqual(drug["indication_summary"], "chronic hepatitis B virus infection")

    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_echoed_format_line_then_answer(self, mock_urlopen, mock_sleep):
        mock_urlopen.return_value = _ollama_reply("CACHE_KEY|condition_name\nNDA221291|ischemic stroke")
        drug = _drug("NDA221291", "SUNHARBO")
        cache = {}
        fda_approvals.summarize_indications_batch([drug], cache)
        self.assertEqual(drug["indication_summary"], "ischemic stroke")

    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_placeholder_only_reply_falls_back_uncached(self, mock_urlopen, mock_sleep):
        mock_urlopen.return_value = _ollama_reply("CACHE_KEY|condition_name")
        drug = _drug()
        cache = {}
        result = fda_approvals.summarize_indications_batch([drug], cache)
        self.assertEqual(result, (0, 1))
        self.assertEqual(cache, {})
        self.assertEqual(drug["indication_summary"], "HIBSAGO")

    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_bad_cached_value_is_resummarized(self, mock_urlopen, mock_sleep):
        """A brand-name fallback saved by older code is not trusted from the cache."""
        mock_urlopen.return_value = _ollama_reply("chronic hepatitis B")
        drug = _drug()
        key = fda_approvals.indication_cache_key(drug)
        cache = {key: "HIBSAGO"}
        fda_approvals.summarize_indications_batch([drug], cache)
        self.assertEqual(cache[key], "chronic hepatitis B")
        mock_urlopen.assert_called_once()

    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_good_cached_value_skips_model(self, mock_urlopen, mock_sleep):
        drug = _drug()
        key = fda_approvals.indication_cache_key(drug)
        cache = {key: "chronic hepatitis B"}
        self.assertEqual(fda_approvals.summarize_indications_batch([drug], cache), (0, 0))
        mock_urlopen.assert_not_called()
        self.assertEqual(drug["indication_summary"], "chronic hepatitis B")


class TestParseConditionReply(unittest.TestCase):
    def test_think_leak(self):
        reply = "moderate to severe HS</think>BLA761349:SUPPL:13:2026-10-15|hidradenitis suppurativa"
        self.assertEqual(fda_approvals.parse_condition_reply(reply), "hidradenitis suppurativa")

    def test_think_block(self):
        self.assertEqual(fda_approvals.parse_condition_reply("<think>hmm</think>\nPlaque psoriasis."), "Plaque psoriasis")

    def test_rejects_raw_label_text(self):
        reply = "adult patients with metastatic NSCLC who have disease progression during or after chemotherapy"
        self.assertEqual(fda_approvals.parse_condition_reply(reply), "")

    def test_rejects_brand_name(self):
        self.assertEqual(fda_approvals.parse_condition_reply("Olumiant", {"brand_name": "OLUMIANT"}), "")

    def test_empty(self):
        self.assertEqual(fda_approvals.parse_condition_reply(""), "")


class TestLoadIndicationSummaries(unittest.TestCase):
    def test_missing_file(self):
        """Test returning empty dict when the file doesn't exist."""
        result = fda_approvals.load_indication_summaries("/nonexistent/file/path.json")
        self.assertEqual(result, {})

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data='{"NDA123": "Summary"}')
    @patch('os.path.exists', return_value=True)
    def test_valid_json(self, mock_exists, mock_file):
        """Test parsing valid JSON file."""
        result = fda_approvals.load_indication_summaries("dummy_path.json")
        self.assertEqual(result, {"NDA123": "Summary"})
        mock_file.assert_called_once_with("dummy_path.json")

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data='invalid json')
    @patch('os.path.exists', return_value=True)
    def test_invalid_json(self, mock_exists, mock_file):
        """Test returning empty dict when handling json.JSONDecodeError."""
        result = fda_approvals.load_indication_summaries("dummy_path.json")
        self.assertEqual(result, {})

    @patch('builtins.open')
    @patch('os.path.exists', return_value=True)
    def test_os_error(self, mock_exists, mock_file):
        """Test returning empty dict when handling OSError."""
        mock_file.side_effect = OSError("Mocked OS Error")
        result = fda_approvals.load_indication_summaries("dummy_path.json")
        self.assertEqual(result, {})

class TestSaveIndicationSummaries(unittest.TestCase):
    def test_creates_file_and_writes_json(self):
        """Test that it correctly writes the dictionary to a JSON file."""
        import tempfile
        import json
        import os

        summaries = {"NDA123": "Disease A", "NDA456": "Disease B"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            cache_path = f.name

        try:
            fda_approvals.save_indication_summaries(summaries, cache_path)

            with open(cache_path) as cf:
                data = json.load(cf)

            self.assertEqual(data, summaries)
        finally:
            os.unlink(cache_path)

    def test_creates_parent_directory(self):
        """Test that it creates parent directories if they don't exist."""
        import tempfile
        import os
        import json
        import shutil

        summaries = {"NDA789": "Disease C"}
        tmpdir = tempfile.mkdtemp()

        try:
            nested_path = os.path.join(tmpdir, "nested", "dirs", "summaries.json")

            self.assertFalse(os.path.exists(os.path.dirname(nested_path)))

            fda_approvals.save_indication_summaries(summaries, nested_path)

            self.assertTrue(os.path.exists(nested_path))

            with open(nested_path) as f:
                data = json.load(f)
            self.assertEqual(data, summaries)
        finally:
            shutil.rmtree(tmpdir)

    def test_replace_failure_preserves_existing_summaries_file(self):
        """If atomic replacement fails, the previous summaries file remains intact."""
        import tempfile
        import json
        import os

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"NDAOLD": "Old Disease"}, f)
            cache_path = f.name

        try:
            with patch("fda_approvals.os.replace", side_effect=OSError("replace failed")):
                with self.assertRaises(OSError):
                    fda_approvals.save_indication_summaries({"NDANEW": "New Disease"}, cache_path)

            with open(cache_path) as cf:
                self.assertEqual(json.load(cf), {"NDAOLD": "Old Disease"})
        finally:
            os.unlink(cache_path)

if __name__ == '__main__':
    unittest.main()
