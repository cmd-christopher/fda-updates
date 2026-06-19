#!/usr/bin/env python3
"""Tests verifying logging behavior on important code paths in fda_approvals.py and build.py.

Uses ``self.assertLogs`` to capture and assert on log records emitted by the
module-level ``logger`` (``logging.getLogger("fda_approvals")`` / ``logging.getLogger("build")``).
"""

import io
import json
import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError

import fda_approvals
import build


class TestFetchJsonLogging(unittest.TestCase):
    """Verify logging in fetch_json retry / failure paths."""

    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_retries_log_warning(self, mock_urlopen, mock_sleep):
        """Transient HTTP 500 should emit a warning log before retrying."""
        err = HTTPError(url='http://example.com/api', code=500, msg='Server Error', hdrs={}, fp=io.BytesIO(b''))
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"status": "ok"}'
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        mock_urlopen.side_effect = [err, mock_cm]

        url = "https://example.com/api"
        with self.assertLogs("fda_approvals", level="WARNING") as cm:
            result = fda_approvals.fetch_json(url)

        self.assertEqual(result, {"status": "ok"})
        # At least one warning about retrying should be present
        retry_logs = [r for r in cm.records if "retrying" in r.getMessage()]
        self.assertTrue(retry_logs, "Expected a retry warning log")
        # The log should include the URL and http_code
        msg = retry_logs[0].getMessage()
        self.assertIn(url, msg)
        self.assertIn("500", msg)

    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_url_error_logs_error_after_exhausting_retries(self, mock_urlopen, mock_sleep):
        """URLError that exhausts retries should emit an error log."""
        mock_urlopen.side_effect = URLError("Connection refused")

        with self.assertLogs("fda_approvals", level="ERROR") as cm:
            with self.assertRaises(URLError):
                fda_approvals.fetch_json("https://example.com/api")

        error_logs = [r for r in cm.records if "fetch_json failed" in r.getMessage()]
        self.assertTrue(error_logs, "Expected an error log for exhausted retries")

    @patch('fda_approvals.urlopen')
    def test_non_retryable_http_error_logs_error(self, mock_urlopen):
        """A non-retryable HTTP error (404) should emit an error log."""
        err = HTTPError(url='http://example.com/api', code=404, msg='Not Found', hdrs={}, fp=io.BytesIO(b''))
        mock_urlopen.side_effect = err

        with self.assertLogs("fda_approvals", level="ERROR") as cm:
            with self.assertRaises(HTTPError):
                fda_approvals.fetch_json("https://example.com/api")

        error_logs = [r for r in cm.records if "fetch_json failed" in r.getMessage()]
        self.assertTrue(error_logs, "Expected an error log for non-retryable HTTP error")
        self.assertIn("404", error_logs[0].getMessage())


class TestFetchPaginatedResultsLogging(unittest.TestCase):
    """Verify logging in _fetch_paginated_results."""

    @patch("fda_approvals.fetch_json")
    def test_completion_logs_total_fetched(self, mock_fetch_json):
        """After pagination completes, an info log with the total count should be emitted."""
        mock_fetch_json.return_value = {
            "meta": {"results": {"total": 1}},
            "results": [{"id": 1}],
        }

        with self.assertLogs("fda_approvals", level="INFO") as cm:
            results = fda_approvals._fetch_paginated_results("http://example.com?query=1", limit=10)

        self.assertEqual(len(results), 1)
        info_logs = [r for r in cm.records if "fetch_paginated complete" in r.getMessage()]
        self.assertTrue(info_logs, "Expected a completion info log")
        self.assertIn("total_fetched=1", info_logs[0].getMessage())


class TestFetchLabelLogging(unittest.TestCase):
    """Verify logging in fetch_label error paths."""

    @patch('fda_approvals.urlopen')
    @patch('fda_approvals.time.sleep')
    def test_http_404_logs_debug(self, mock_sleep, mock_urlopen):
        """HTTP 404 in fetch_label should emit a debug log (not a warning)."""
        err = HTTPError(url='http://test.com', code=404, msg='Not Found', hdrs={}, fp=io.BytesIO(b''))
        mock_urlopen.side_effect = err

        drug = {"application_number": "NDA123456", "brand_name": "TestDrug"}

        # assertLogs at DEBUG level captures debug+ records
        with self.assertLogs("fda_approvals", level="DEBUG") as cm:
            result = fda_approvals.fetch_label(drug)

        self.assertIsNone(result)
        debug_logs = [r for r in cm.records if "no_label" in r.getMessage() and r.levelname == "DEBUG"]
        self.assertTrue(debug_logs, "Expected a debug log for 404 no-label")
        self.assertIn("NDA123456", debug_logs[0].getMessage())

    @patch('fda_approvals.urlopen')
    @patch('fda_approvals.time.sleep')
    def test_http_500_logs_warning(self, mock_sleep, mock_urlopen):
        """HTTP 500 in fetch_label should emit a warning log with app_num and name."""
        err = HTTPError(url='http://test.com', code=500, msg='Internal Server Error', hdrs={}, fp=io.BytesIO(b''))
        mock_urlopen.side_effect = err

        drug = {"application_number": "NDA123456", "brand_name": "TestDrug"}

        with self.assertLogs("fda_approvals", level="WARNING") as cm:
            result = fda_approvals.fetch_label(drug)

        self.assertIsNone(result)
        warn_logs = [r for r in cm.records if "fetch_label failed" in r.getMessage()]
        self.assertTrue(warn_logs, "Expected a warning log for HTTP 500")
        msg = warn_logs[0].getMessage()
        self.assertIn("NDA123456", msg)
        self.assertIn("TestDrug", msg)
        self.assertIn("500", msg)


class TestLoadIndicationSummariesLogging(unittest.TestCase):
    """Verify logging in load_indication_summaries."""

    def test_missing_file_logs_debug(self):
        """Missing cache file should emit a debug log."""
        with self.assertLogs("fda_approvals", level="DEBUG") as cm:
            result = fda_approvals.load_indication_summaries("/nonexistent/file/path.json")

        self.assertEqual(result, {})
        debug_logs = [r for r in cm.records if "not_found" in r.getMessage()]
        self.assertTrue(debug_logs, "Expected a debug log for missing file")

    def test_valid_json_logs_info_with_count(self):
        """Successfully loaded cache should emit an info log with entry count."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"NDA123": "Disease A", "NDA456": "Disease B"}, f)
            path = f.name
        try:
            with self.assertLogs("fda_approvals", level="INFO") as cm:
                result = fda_approvals.load_indication_summaries(path)

            self.assertEqual(len(result), 2)
            info_logs = [r for r in cm.records if "entries=" in r.getMessage()]
            self.assertTrue(info_logs, "Expected an info log with entry count")
            self.assertIn("entries=2", info_logs[0].getMessage())
        finally:
            os.unlink(path)

    def test_corrupt_json_logs_warning(self):
        """Corrupt JSON should emit a warning log."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("NOT VALID JSON{{{")
            path = f.name
        try:
            with self.assertLogs("fda_approvals", level="WARNING") as cm:
                result = fda_approvals.load_indication_summaries(path)

            self.assertEqual(result, {})
            warn_logs = [r for r in cm.records if "returning_empty" in r.getMessage()]
            self.assertTrue(warn_logs, "Expected a warning log for corrupt JSON")
        finally:
            os.unlink(path)


class TestLoadPreviousApprovalsLogging(unittest.TestCase):
    """Verify logging in load_previous_approvals."""

    def test_missing_file_logs_debug(self):
        """Missing previous approvals file should emit a debug log."""
        with self.assertLogs("fda_approvals", level="DEBUG") as cm:
            result = fda_approvals.load_previous_approvals("/nonexistent/path.json")

        self.assertEqual(result, {})
        debug_logs = [r for r in cm.records if "not_found" in r.getMessage()]
        self.assertTrue(debug_logs, "Expected a debug log for missing file")

    def test_valid_file_logs_info_with_count(self):
        """Valid previous approvals file should emit an info log with cached entry count."""
        drugs = [
            {
                "application_number": "NDA123456",
                "brand_name": "TestDrug",
                "label": {"indications_and_usage": ["Test"], "set_id": "uuid-1"},
            },
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"drugs": drugs}, f)
            path = f.name
        try:
            with self.assertLogs("fda_approvals", level="INFO") as cm:
                result = fda_approvals.load_previous_approvals(path)

            self.assertIn("NDA123456", result)
            info_logs = [r for r in cm.records if "cached_entries=" in r.getMessage()]
            self.assertTrue(info_logs, "Expected an info log with cached entry count")
        finally:
            os.unlink(path)

    def test_corrupt_json_logs_warning(self):
        """Corrupt JSON should emit a warning log."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("NOT VALID JSON{{{")
            path = f.name
        try:
            with self.assertLogs("fda_approvals", level="WARNING") as cm:
                result = fda_approvals.load_previous_approvals(path)

            self.assertEqual(result, {})
            warn_logs = [r for r in cm.records if "returning_empty" in r.getMessage()]
            self.assertTrue(warn_logs, "Expected a warning log for corrupt JSON")
        finally:
            os.unlink(path)


class TestWriteTextAtomicLogging(unittest.TestCase):
    """Verify logging in write_text_atomic."""

    def test_success_logs_debug(self):
        """Successful atomic write should emit a debug log."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            path = f.name
        try:
            os.unlink(path)  # remove so write creates fresh
            with self.assertLogs("fda_approvals", level="DEBUG") as cm:
                fda_approvals.write_text_atomic(path, "hello world")

            debug_logs = [r for r in cm.records if "write_text_atomic" in r.getMessage() and "bytes=" in r.getMessage()]
            self.assertTrue(debug_logs, "Expected a debug log for successful write")
            self.assertIn("bytes=11", debug_logs[0].getMessage())
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_failure_logs_error(self):
        """Failed atomic write should emit an error log."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            path = f.name
        try:
            with patch("fda_approvals.os.replace", side_effect=OSError("replace failed")):
                with self.assertLogs("fda_approvals", level="ERROR") as cm:
                    with self.assertRaises(OSError):
                        fda_approvals.write_text_atomic(path, "data")

            error_logs = [r for r in cm.records if "write_text_atomic failed" in r.getMessage()]
            self.assertTrue(error_logs, "Expected an error log for failed write")
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestFetchDrugsfdaApprovalsLogging(unittest.TestCase):
    """Verify logging in fetch_drugsfda_approvals."""

    @patch('fda_approvals._fetch_paginated_results')
    def test_logs_url_and_counts(self, mock_fetch):
        """fetch_drugsfda_approvals should log the request URL and filtered count."""
        valid_record = {
            "application_number": "NDA001",
            "openfda": {"brand_name": ["ValidBrand"], "generic_name": ["ValidGeneric"]},
            "submissions": [
                {"submission_type": "ORIG", "submission_status": "AP", "submission_status_date": "20230115"}
            ],
            "products": [{"marketing_status": "Prescription"}],
        }
        mock_fetch.return_value = [valid_record]

        date_from = datetime(2023, 1, 1)
        date_to = datetime(2023, 1, 31)

        with self.assertLogs("fda_approvals", level="INFO") as cm:
            result = fda_approvals.fetch_drugsfda_approvals(date_from, date_to)

        self.assertEqual(len(result), 1)
        all_logs = [r.getMessage() for r in cm.records]
        # Should log the URL at start
        self.assertTrue(any("fetch_drugsfda_approvals url=" in m for m in all_logs),
                        f"Expected URL log, got: {all_logs}")
        # Should log filtered count at end
        self.assertTrue(any("filtered_drugs=1" in m for m in all_logs),
                        f"Expected filtered_drugs log, got: {all_logs}")


class TestFetchSupplApprovalsLogging(unittest.TestCase):
    """Verify logging in fetch_suppl_approvals."""

    @patch('fda_approvals._fetch_paginated_results')
    def test_logs_url_and_empty_count(self, mock_fetch):
        """fetch_suppl_approvals should log the request URL and filtered count."""
        mock_fetch.return_value = []

        date_from = datetime(2023, 1, 1)
        date_to = datetime(2023, 1, 31)

        with self.assertLogs("fda_approvals", level="INFO") as cm:
            result = fda_approvals.fetch_suppl_approvals(date_from, date_to)

        self.assertEqual(len(result), 0)
        all_logs = [r.getMessage() for r in cm.records]
        self.assertTrue(any("fetch_suppl_approvals url=" in m for m in all_logs),
                        f"Expected URL log, got: {all_logs}")
        self.assertTrue(any("filtered_drugs=0" in m for m in all_logs),
                        f"Expected filtered_drugs=0 log, got: {all_logs}")


class TestSummarizeIndicationsBatchLogging(unittest.TestCase):
    """Verify logging in summarize_indications_batch."""

    @patch('fda_approvals.urlopen')
    @patch('fda_approvals.time.sleep')
    def test_batch_failure_logs_warning(self, mock_sleep, mock_urlopen):
        """LLM API failure should emit a warning log with batch context."""
        mock_urlopen.side_effect = Exception("Mocked API Error")

        drugs = [
            {
                "application_number": "NDA123",
                "brand_name": "TestBrand",
                "generic_name": "TestGeneric",
                "label": {"indications_and_usage": ["Treats disease A"]},
            },
        ]
        summaries_cache = {}

        with self.assertLogs("fda_approvals", level="INFO") as cm:
            fda_approvals.summarize_indications_batch(drugs, "test_key", summaries_cache)

        # Should log the start info
        info_logs = [r for r in cm.records if "to_process=" in r.getMessage()]
        self.assertTrue(info_logs, "Expected an info log with to_process count")

        # Should log a warning for the failed batch
        warn_logs = [r for r in cm.records if "summarize_indications_batch failed" in r.getMessage()]
        self.assertTrue(warn_logs, "Expected a warning log for batch failure")
        self.assertIn("using_fallback", warn_logs[0].getMessage())


class TestFetchPdfTextLogging(unittest.TestCase):
    """Verify logging in fetch_pdf_text."""

    @patch('fda_approvals.shutil.which', return_value=None)
    def test_no_pdftotext_returns_empty(self, mock_which):
        """When pdftotext is not available, fetch_pdf_text returns empty string."""
        result = fda_approvals.fetch_pdf_text("https://example.com/test.pdf")
        self.assertEqual(result, "")

    @patch('fda_approvals.subprocess.run')
    @patch('fda_approvals.urlopen')
    @patch('fda_approvals.shutil.which', return_value="/usr/bin/pdftotext")
    def test_pdftotext_failure_logs_warning(self, mock_which, mock_urlopen, mock_run):
        """pdftotext returning non-zero exit should emit a warning log."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"fake pdf bytes"
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_cm

        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        with self.assertLogs("fda_approvals", level="WARNING") as cm:
            result = fda_approvals.fetch_pdf_text("https://example.com/test.pdf")

        self.assertEqual(result, "")
        warn_logs = [r for r in cm.records if "pdftotext_failed" in r.getMessage()]
        self.assertTrue(warn_logs, "Expected a warning log for pdftotext failure")
        self.assertIn("https://example.com/test.pdf", warn_logs[0].getMessage())


class TestProcessLabelsLogging(unittest.TestCase):
    """Verify logging in process_labels."""

    def test_skip_labels_logs_info(self):
        """process_labels with skip_labels should emit an info log."""
        class Args:
            skip_labels = True
            cache = False

        drugs = [{"application_number": "NDA001", "brand_name": "TestDrug"}]

        with self.assertLogs("fda_approvals", level="INFO") as cm:
            result = fda_approvals.process_labels(Args, drugs)

        self.assertEqual(len(result), 1)
        info_logs = [r for r in cm.records if "skip_labels" in r.getMessage()]
        self.assertTrue(info_logs, "Expected an info log for skip_labels stage")
        self.assertIn("total_drugs=1", info_logs[0].getMessage())


class TestWriteOutputLogging(unittest.TestCase):
    """Verify logging in write_output."""

    def test_file_output_logs_info(self):
        """write_output to a file should emit an info log with path and count."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        class Args:
            date_from = "2026-01-01"
            date_to = "2026-01-31"
            submission_type = "all"
            output = path

        try:
            with self.assertLogs("fda_approvals", level="INFO") as cm:
                fda_approvals.write_output(Args, [{"application_number": "NDANEW"}])

            info_logs = [r for r in cm.records if "write_output" in r.getMessage()]
            self.assertTrue(info_logs, "Expected an info log for write_output")
            self.assertIn(path, info_logs[0].getMessage())
            self.assertIn("drug_count=1", info_logs[0].getMessage())
        finally:
            os.unlink(path)


class TestBuildLogging(unittest.TestCase):
    """Verify logging in build.py functions."""

    def test_verify_assets_missing_logs_error(self):
        """verify_assets should log an error for missing assets."""
        # All REQUIRED_ASSETS will be missing in a clean temp cwd
        with patch("build.REQUIRED_ASSETS", ["/nonexistent/asset.css"]):
            with self.assertLogs("build", level="ERROR") as cm:
                with self.assertRaises(SystemExit):
                    build.verify_assets()

            error_logs = [r for r in cm.records if "missing asset" in r.getMessage()]
            self.assertTrue(error_logs, "Expected an error log for missing asset")

    def test_load_data_missing_file_logs_error(self):
        """load_data should log an error when data file is missing."""
        with patch("build.DATA_PATH", "/nonexistent/data.json"):
            with self.assertLogs("build", level="ERROR") as cm:
                with self.assertRaises(SystemExit):
                    build.load_data()

            error_logs = [r for r in cm.records if "load_data missing" in r.getMessage()]
            self.assertTrue(error_logs, "Expected an error log for missing data file")

    def test_load_data_corrupt_json_logs_error(self):
        """load_data should log an error for corrupt JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("NOT VALID JSON{{{")
            path = f.name
        try:
            with patch("build.DATA_PATH", path):
                with self.assertLogs("build", level="ERROR") as cm:
                    with self.assertRaises(SystemExit):
                        build.load_data()

                error_logs = [r for r in cm.records if "load_data failed" in r.getMessage()]
                self.assertTrue(error_logs, "Expected an error log for corrupt JSON")
        finally:
            os.unlink(path)

    def test_load_data_valid_logs_info(self):
        """load_data should log an info with drug count on success."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"drugs": [{"brand_name": "X"}]}, f)
            path = f.name
        try:
            with patch("build.DATA_PATH", path):
                with self.assertLogs("build", level="INFO") as cm:
                    data = build.load_data()

                self.assertEqual(len(data["drugs"]), 1)
                info_logs = [r for r in cm.records if "drug_count=" in r.getMessage()]
                self.assertTrue(info_logs, "Expected an info log with drug count")
                self.assertIn("drug_count=1", info_logs[0].getMessage())
        finally:
            os.unlink(path)

    def test_validate_drug_data_missing_field_logs_error(self):
        """validate_drug_data should log an error for a missing required field."""
        drugs = [{"brand_name": "TestDrug", "generic_name": "TestGeneric"}]
        # Missing: approval_date, application_number, type_badge, slug

        with self.assertLogs("build", level="ERROR") as cm:
            with self.assertRaises(SystemExit):
                build.validate_drug_data(drugs)

        error_logs = [r for r in cm.records if "missing field" in r.getMessage()]
        self.assertTrue(error_logs, "Expected an error log for missing field")
        self.assertIn("approval_date", error_logs[0].getMessage())

    def test_validate_drug_data_valid_logs_info(self):
        """validate_drug_data should log an info on success."""
        drugs = [{
            "brand_name": "TestDrug",
            "generic_name": "TestGeneric",
            "approval_date": "2026-01-01",
            "application_number": "NDA123",
            "type_badge": "New Drug",
            "slug": "testdrug",
        }]

        with self.assertLogs("build", level="INFO") as cm:
            build.validate_drug_data(drugs)

        info_logs = [r for r in cm.records if "validate_drug_data valid" in r.getMessage()]
        self.assertTrue(info_logs, "Expected an info log for valid data")
        self.assertIn("count=1", info_logs[0].getMessage())


if __name__ == "__main__":
    unittest.main()