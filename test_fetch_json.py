#!/usr/bin/env python3
"""Unit tests for fetch_json in fda_approvals.py."""

import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError
import io
import json

import fda_approvals

class TestFetchJson(unittest.TestCase):
    """Test fetch_json functionality."""

    @patch('fda_approvals.urlopen')
    @patch('fda_approvals.Request')
    def test_fetch_json_success(self, mock_request_class, mock_urlopen):
        """Test fetch_json successfully parses a valid JSON response."""
        # Setup mocks
        mock_request = MagicMock()
        mock_request_class.return_value = mock_request

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"status": "ok", "count": 42}'

        # Setup context manager for urlopen
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_cm

        url = "https://example.com/api"
        result = fda_approvals.fetch_json(url)

        # Assert Request was instantiated correctly
        mock_request_class.assert_called_once_with(url, headers={"User-Agent": "fda-approvals-script/1.0"})
        # Assert urlopen was called correctly
        mock_urlopen.assert_called_once_with(mock_request, timeout=30)
        # Assert result is correctly parsed
        self.assertEqual(result, {"status": "ok", "count": 42})

    @patch('fda_approvals.urlopen')
    def test_fetch_json_invalid_json(self, mock_urlopen):
        """Test fetch_json raises JSONDecodeError when receiving invalid JSON."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'invalid json'

        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_cm

        with self.assertRaises(json.JSONDecodeError):
            fda_approvals.fetch_json("https://example.com/api")

    @patch('fda_approvals.urlopen')
    def test_fetch_json_http_error(self, mock_urlopen):
        """Test fetch_json raises HTTPError when the server responds with an HTTP error."""
        err = HTTPError(url='http://example.com/api', code=404, msg='Not Found', hdrs={}, fp=io.BytesIO(b''))
        mock_urlopen.side_effect = err

        with self.assertRaises(HTTPError):
            fda_approvals.fetch_json("https://example.com/api")

    @patch('fda_approvals.urlopen')
    def test_fetch_json_url_error(self, mock_urlopen):
        """Test fetch_json raises URLError when there is a connection issue."""
        err = URLError("Connection refused")
        mock_urlopen.side_effect = err

        with self.assertRaises(URLError):
            fda_approvals.fetch_json("https://example.com/api")

if __name__ == '__main__':
    unittest.main()
