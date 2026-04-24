#!/usr/bin/env python3
"""Unit tests for fetch_label HTTP error handling in fda_approvals.py."""

import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import io

# Import the module under test
import fda_approvals

class TestFetchLabelHTTPErrorHandling(unittest.TestCase):
    """Test HTTP error handling in the fetch_label() function."""

    @patch('fda_approvals.urlopen')
    @patch('fda_approvals.time.sleep')
    def test_fetch_label_http_404(self, mock_sleep, mock_urlopen):
        """When an HTTP 404 error occurs, fetch_label should return None without error output."""
        # Setup mock to raise HTTPError with code 404
        err = HTTPError(url='http://test.com', code=404, msg='Not Found', hdrs={}, fp=io.BytesIO(b''))
        mock_urlopen.side_effect = err

        drug = {"application_number": "NDA123456", "brand_name": "TestDrug"}

        # We capture stderr just to ensure nothing is written
        with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            result = fda_approvals.fetch_label(drug)

            # Should return None
            self.assertIsNone(result)
            # Should not print a warning
            self.assertEqual(mock_stderr.getvalue(), "")

    @patch('fda_approvals.urlopen')
    @patch('fda_approvals.time.sleep')
    def test_fetch_label_http_500(self, mock_sleep, mock_urlopen):
        """When an HTTP 500 error occurs, fetch_label should return None and print a warning."""
        # Setup mock to raise HTTPError with code 500
        err = HTTPError(url='http://test.com', code=500, msg='Internal Server Error', hdrs={}, fp=io.BytesIO(b''))
        mock_urlopen.side_effect = err

        drug = {"application_number": "NDA123456", "brand_name": "TestDrug"}

        # Capture stderr to verify warning message
        with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            result = fda_approvals.fetch_label(drug)

            # Should return None
            self.assertIsNone(result)
            # Should print a warning containing the error code and drug name
            stderr_output = mock_stderr.getvalue()
            self.assertIn("Warning: HTTP 500", stderr_output)
            self.assertIn("TestDrug", stderr_output)

if __name__ == '__main__':
    unittest.main()
