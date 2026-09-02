#!/usr/bin/env python3
"""Unit tests for fetch_label HTTP error handling in fda_approvals.py."""

import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError
import io
import json

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
        with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr, \
             patch('fda_approvals.logger.error'):
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

class TestRetryDelay(unittest.TestCase):
    def test_429_with_retry_after(self):
        err = HTTPError(url="http://x", code=429, msg="x", hdrs={"Retry-After": "5"}, fp=io.BytesIO(b""))
        self.assertEqual(fda_approvals._retry_delay(0, err), 5.0)

    def test_429_with_invalid_retry_after(self):
        err = HTTPError(url="http://x", code=429, msg="x", hdrs={"Retry-After": "abc"}, fp=io.BytesIO(b""))
        # Invalid Retry-After -> falls through to exponential backoff
        self.assertEqual(fda_approvals._retry_delay(0, err), 1.0)

    def test_429_no_headers(self):
        err = HTTPError(url="http://x", code=429, msg="x", hdrs=None, fp=io.BytesIO(b""))
        self.assertEqual(fda_approvals._retry_delay(2, err), 4.0)

    def test_429_no_retry_after_header(self):
        err = HTTPError(url="http://x", code=429, msg="x", hdrs={}, fp=io.BytesIO(b""))
        self.assertEqual(fda_approvals._retry_delay(1, err), 2.0)

    def test_non_429_error(self):
        err = HTTPError(url="http://x", code=500, msg="x", hdrs={}, fp=io.BytesIO(b""))
        self.assertEqual(fda_approvals._retry_delay(0, err), 1.0)

    def test_url_error(self):
        err = URLError("timeout")
        self.assertEqual(fda_approvals._retry_delay(1, err), 2.0)


# ---------------------------------------------------------------------------
# fetch_json — unreachable RuntimeError and Retry-After
# ---------------------------------------------------------------------------

class TestFetchJsonEdgeCases(unittest.TestCase):
    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_429_retry_after_header_used(self, mock_urlopen, mock_sleep):
        """429 with Retry-After header should sleep that duration and retry."""
        err = HTTPError(url='http://x', code=429, msg='x', hdrs={"Retry-After": "3"}, fp=io.BytesIO(b''))
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok": true}'
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        mock_urlopen.side_effect = [err, mock_cm]

        result = fda_approvals.fetch_json("https://example.com/api")
        self.assertEqual(result, {"ok": True})
        # sleep called with 3.0 (from Retry-After)
        mock_sleep.assert_called_once_with(3.0)

    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_exhausts_retries_on_http_500(self, mock_urlopen, mock_sleep):
        """HTTP 500 that exhausts all retries should raise and log error."""
        err = HTTPError(url='http://x', code=500, msg='Server Error', hdrs={}, fp=io.BytesIO(b''))
        mock_urlopen.side_effect = err

        with self.assertRaises(HTTPError):
            fda_approvals.fetch_json("https://example.com/api", max_retries=2)
        self.assertEqual(mock_urlopen.call_count, 2)


# ---------------------------------------------------------------------------
# extract_short_indication — additional branches
# ---------------------------------------------------------------------------

class TestFetchJsonEdgeCases(unittest.TestCase):
    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_429_retry_after_header_used(self, mock_urlopen, mock_sleep):
        """429 with Retry-After header should sleep that duration and retry."""
        err = HTTPError(url='http://x', code=429, msg='x', hdrs={"Retry-After": "3"}, fp=io.BytesIO(b''))
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok": true}'
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        mock_urlopen.side_effect = [err, mock_cm]

        result = fda_approvals.fetch_json("https://example.com/api")
        self.assertEqual(result, {"ok": True})
        # sleep called with 3.0 (from Retry-After)
        mock_sleep.assert_called_once_with(3.0)

    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_exhausts_retries_on_http_500(self, mock_urlopen, mock_sleep):
        """HTTP 500 that exhausts all retries should raise and log error."""
        err = HTTPError(url='http://x', code=500, msg='Server Error', hdrs={}, fp=io.BytesIO(b''))
        mock_urlopen.side_effect = err

        with self.assertRaises(HTTPError):
            fda_approvals.fetch_json("https://example.com/api", max_retries=2)
        self.assertEqual(mock_urlopen.call_count, 2)


# ---------------------------------------------------------------------------
# extract_short_indication — additional branches
# ---------------------------------------------------------------------------

class TestFetchLabelSuccess(unittest.TestCase):
    @patch('fda_approvals.api_rate_limiter')
    @patch('fda_approvals.fetch_json')
    def test_success_returns_label_data(self, mock_fetch_json, mock_limiter):
        mock_fetch_json.return_value = {
            "results": [
                {
                    "id": "abc-123",
                    "indications_and_usage": ["treats disease"],
                    "boxed_warning": ["warning text"],
                    "openfda": {"rxcui": ["123"]},
                }
            ]
        }
        drug = {"application_number": "NDA123", "brand_name": "TestDrug"}
        result = fda_approvals.fetch_label(drug)

        self.assertIsNotNone(result)
        self.assertEqual(result["set_id"], "abc-123")
        self.assertIn("indications_and_usage", result)
        self.assertIn("boxed_warning", result)
        self.assertEqual(result["openfda"], {"rxcui": ["123"]})

    @patch('fda_approvals.api_rate_limiter')
    @patch('fda_approvals.fetch_json')
    def test_no_results_returns_none(self, mock_fetch_json, mock_limiter):
        mock_fetch_json.return_value = {"results": []}
        drug = {"application_number": "NDA123", "brand_name": "TestDrug"}
        self.assertIsNone(fda_approvals.fetch_label(drug))

    @patch('fda_approvals.api_rate_limiter')
    @patch('fda_approvals.fetch_json')
    def test_results_missing_fields(self, mock_fetch_json, mock_limiter):
        """Label fields that are empty/None should be skipped."""
        mock_fetch_json.return_value = {
            "results": [
                {
                    "id": "abc-456",
                    "indications_and_usage": "",
                    "boxed_warning": None,
                    "openfda": {},
                }
            ]
        }
        drug = {"application_number": "NDA123", "brand_name": "TestDrug"}
        result = fda_approvals.fetch_label(drug)
        self.assertIsNotNone(result)
        self.assertNotIn("indications_and_usage", result)  # empty string skipped
        self.assertNotIn("boxed_warning", result)  # None skipped

    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_url_error_returns_none(self, mock_urlopen, mock_sleep):
        """URLError (non-HTTP) should return None and print a warning."""
        mock_urlopen.side_effect = URLError("connection refused")
        drug = {"application_number": "NDA123", "brand_name": "TestDrug"}
        with patch('sys.stderr', new_callable=io.StringIO):
            result = fda_approvals.fetch_label(drug)
        self.assertIsNone(result)

    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_json_decode_error_returns_none(self, mock_urlopen, mock_sleep):
        """json.JSONDecodeError should return None and print a warning."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'invalid json'
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_cm
        drug = {"application_number": "NDA123", "brand_name": "TestDrug"}
        with patch('sys.stderr', new_callable=io.StringIO):
            result = fda_approvals.fetch_label(drug)
        self.assertIsNone(result)

    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_http_error_no_brand_uses_generic_name(self, mock_urlopen, mock_sleep):
        """HTTP error with no brand_name should fall back to generic_name in log."""
        err = HTTPError(url='http://x', code=500, msg='x', hdrs={}, fp=io.BytesIO(b''))
        mock_urlopen.side_effect = err
        drug = {"application_number": "NDA123", "generic_name": "GenName"}
        with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            result = fda_approvals.fetch_label(drug)
        self.assertIsNone(result)
        self.assertIn("GenName", mock_stderr.getvalue())

    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_http_error_no_names_uses_unknown(self, mock_urlopen, mock_sleep):
        """HTTP error with no names should use 'Unknown' in log."""
        err = HTTPError(url='http://x', code=500, msg='x', hdrs={}, fp=io.BytesIO(b''))
        mock_urlopen.side_effect = err
        drug = {"application_number": "NDA123"}
        with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            result = fda_approvals.fetch_label(drug)
        self.assertIsNone(result)
        self.assertIn("Unknown", mock_stderr.getvalue())

    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_url_error_no_names_uses_unknown(self, mock_urlopen, mock_sleep):
        """URLError with no names should use 'Unknown' in warning."""
        mock_urlopen.side_effect = URLError("conn refused")
        drug = {"application_number": "NDA123"}
        with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            result = fda_approvals.fetch_label(drug)
        self.assertIsNone(result)
        self.assertIn("Unknown", mock_stderr.getvalue())


# ---------------------------------------------------------------------------
# _process_drug_label — all branches
# ---------------------------------------------------------------------------
