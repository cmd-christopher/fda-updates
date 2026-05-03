import unittest
from unittest.mock import patch
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
        api_key = "test_key"

        # Run function
        fda_approvals.summarize_indications_batch(drugs, api_key, summaries_cache)

        # Check assertions
        # Expected behavior:
        # summaries_cache[app_num] = brand
        # drug["indication_summary"] = drug.get("brand_name", "") or drug.get("generic_name", "")
        self.assertEqual(summaries_cache["NDA123"], "TestBrand")
        self.assertEqual(drugs[0]["indication_summary"], "TestBrand")

        self.assertEqual(summaries_cache["NDA456"], "GenericBrand")
        self.assertEqual(drugs[1]["indication_summary"], "GenericBrand")

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

if __name__ == '__main__':
    unittest.main()
