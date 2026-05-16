import unittest
from unittest.mock import patch

from fda_approvals import _fetch_paginated_results

class TestFetchPaginatedResults(unittest.TestCase):
    @patch("fda_approvals.fetch_json")
    def test_single_page(self, mock_fetch_json):
        """Test when the first page has fewer results than the limit."""
        mock_fetch_json.return_value = {
            "meta": {"results": {"total": 1}},
            "results": [{"id": 1}]
        }

        results = _fetch_paginated_results("http://example.com?query=1", limit=10)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], 1)
        mock_fetch_json.assert_called_once_with("http://example.com?query=1")

    @patch("fda_approvals.fetch_json")
    def test_multiple_pages_by_limit(self, mock_fetch_json):
        """Test pagination stops when a page returns fewer results than the limit."""
        mock_fetch_json.side_effect = [
            {
                "meta": {"results": {"total": 5}},
                "results": [{"id": 1}, {"id": 2}]
            },
            {
                "meta": {"results": {"total": 5}},
                "results": [{"id": 3}]
            }
        ]

        results = _fetch_paginated_results("http://example.com?query=1", limit=2)

        self.assertEqual(len(results), 3)
        self.assertEqual(mock_fetch_json.call_count, 2)
        mock_fetch_json.assert_any_call("http://example.com?query=1")
        mock_fetch_json.assert_any_call("http://example.com?query=1&skip=2")

    @patch("fda_approvals.fetch_json")
    def test_multiple_pages_by_total(self, mock_fetch_json):
        """Test pagination stops when all_results length reaches the total count."""
        mock_fetch_json.side_effect = [
            {
                "meta": {"results": {"total": 4}},
                "results": [{"id": 1}, {"id": 2}]
            },
            {
                "meta": {"results": {"total": 4}},
                "results": [{"id": 3}, {"id": 4}]
            },
            {
                # Should not be called
                "meta": {"results": {"total": 4}},
                "results": []
            }
        ]

        results = _fetch_paginated_results("http://example.com?query=1", limit=2)

        self.assertEqual(len(results), 4)
        self.assertEqual(mock_fetch_json.call_count, 2)
        mock_fetch_json.assert_any_call("http://example.com?query=1")
        mock_fetch_json.assert_any_call("http://example.com?query=1&skip=2")

    @patch("fda_approvals.fetch_json")
    def test_empty_results(self, mock_fetch_json):
        """Test behavior when API returns empty results."""
        mock_fetch_json.return_value = {
            "meta": {"results": {"total": 0}},
            "results": []
        }

        results = _fetch_paginated_results("http://example.com?query=1", limit=10)

        self.assertEqual(len(results), 0)
        mock_fetch_json.assert_called_once_with("http://example.com?query=1")

    @patch("fda_approvals.fetch_json")
    def test_missing_meta(self, mock_fetch_json):
        """Test behavior when API response is missing meta information.

        When the meta total count is not present, safe_get returns 0.
        The condition len(all_results) >= 0 will evaluate to True, causing the
        pagination loop to break immediately after the first iteration.
        """
        mock_fetch_json.side_effect = [
            {
                "results": [{"id": 1}, {"id": 2}]
            },
            {
                "results": [{"id": 3}]
            }
        ]

        results = _fetch_paginated_results("http://example.com?query=1", limit=2)

        # It actually breaks after first iteration because safe_get returns 0.
        self.assertEqual(len(results), 2)
        self.assertEqual(mock_fetch_json.call_count, 1)

if __name__ == '__main__':
    unittest.main()
