#!/usr/bin/env python3
"""Coverage tests for fda_approvals.py — targeting lines not exercised by existing tests.

Covers: is_non_condition_indication, label_indications_text, indication_source_text,
_retry_delay, fetch_drugsfda_approvals edge cases, fetch_suppl_approvals,
fetch_pdf_text, extract_new_indication_text, fetch_new_indication_text,
fetch_label success, _process_drug_label branches, fetch_all_approvals,
process_labels with cache, summarize_indications, write_output stdout, main, etc.
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch, mock_open
from urllib.error import HTTPError, URLError

import fda_approvals


# ---------------------------------------------------------------------------
# is_non_condition_indication
# ---------------------------------------------------------------------------

class TestIsNonConditionIndication(unittest.TestCase):
    def test_non_string_returns_false(self):
        self.assertFalse(fda_approvals.is_non_condition_indication(None))
        self.assertFalse(fda_approvals.is_non_condition_indication(123))
        self.assertFalse(fda_approvals.is_non_condition_indication(["efficacy"]))

    def test_exact_match_in_set(self):
        self.assertTrue(fda_approvals.is_non_condition_indication("Efficacy"))
        self.assertTrue(fda_approvals.is_non_condition_indication("ORIG"))
        self.assertTrue(fda_approvals.is_non_condition_indication("Suppl"))
        self.assertTrue(fda_approvals.is_non_condition_indication("Original Approval"))
        self.assertTrue(fda_approvals.is_non_condition_indication("Supplement"))

    def test_contains_efficacy(self):
        self.assertTrue(fda_approvals.is_non_condition_indication("efficacy update"))
        self.assertTrue(fda_approvals.is_non_condition_indication("Safety Efficacy Data"))

    def test_real_condition_returns_false(self):
        self.assertFalse(fda_approvals.is_non_condition_indication("plaque psoriasis"))
        self.assertFalse(fda_approvals.is_non_condition_indication("HIV-1 infection"))


# ---------------------------------------------------------------------------
# label_indications_text
# ---------------------------------------------------------------------------

class TestLabelIndicationsText(unittest.TestCase):
    def test_none_label(self):
        self.assertEqual(fda_approvals.label_indications_text(None), "")

    def test_missing_key(self):
        self.assertEqual(fda_approvals.label_indications_text({}), "")

    def test_list_value(self):
        self.assertEqual(fda_approvals.label_indications_text({"indications_and_usage": ["A", "B"]}), "A B")

    def test_string_value(self):
        self.assertEqual(fda_approvals.label_indications_text({"indications_and_usage": "text"}), "text")


# ---------------------------------------------------------------------------
# indication_source_text
# ---------------------------------------------------------------------------

class TestIndicationSourceText(unittest.TestCase):
    def test_new_indication_text_takes_priority(self):
        drug = {"new_indication_text": "new text", "label": {"indications_and_usage": ["old"]}}
        self.assertEqual(fda_approvals.indication_source_text(drug), "new text")

    def test_suppl_with_recent_and_clinical(self):
        drug = {
            "submission_type": "SUPPL",
            "label": {
                "indications_and_usage": ["indication text"],
                "recent_major_changes": ["recent change"],
                "clinical_studies": ["clinical data"],
            },
        }
        result = fda_approvals.indication_source_text(drug)
        self.assertIn("Recent Major Changes: recent change", result)
        self.assertIn("Indications and Usage: indication text", result)
        self.assertIn("Clinical Studies: clinical data", result)

    def test_suppl_with_string_recent_and_clinical(self):
        drug = {
            "submission_type": "SUPPL",
            "label": {
                "indications_and_usage": ["indication text"],
                "recent_major_changes": "string recent",
                "clinical_studies": "string clinical",
            },
        }
        result = fda_approvals.indication_source_text(drug)
        self.assertIn("string recent", result)
        self.assertIn("string clinical", result)

    def test_suppl_no_recent_no_clinical(self):
        drug = {
            "submission_type": "SUPPL",
            "label": {"indications_and_usage": ["only indication"]},
        }
        result = fda_approvals.indication_source_text(drug)
        self.assertIn("only indication", result)

    def test_orig_falls_back_to_submission_class(self):
        drug = {"submission_type": "ORIG", "submission_class": "Type 1 - NME"}
        self.assertEqual(fda_approvals.indication_source_text(drug), "Type 1 - NME")

    def test_orig_falls_back_to_submission_type(self):
        drug = {"submission_type": "ORIG"}
        self.assertEqual(fda_approvals.indication_source_text(drug), "ORIG")

    def test_orig_with_indications(self):
        drug = {"submission_type": "ORIG", "label": {"indications_and_usage": "the disease"}}
        self.assertEqual(fda_approvals.indication_source_text(drug), "the disease")


# ---------------------------------------------------------------------------
# _retry_delay
# ---------------------------------------------------------------------------

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

class TestExtractShortIndicationBranches(unittest.TestCase):
    def test_whitespace_only(self):
        # After strip, text is empty -> return ""
        self.assertEqual(fda_approvals.extract_short_indication("   "), "")

    def test_expand_population_pattern(self):
        text = "To expand the label to include HIV-1 infected pediatric patients weighing at least 14 kg."
        self.assertEqual(
            fda_approvals.extract_short_indication(text),
            "HIV-1 infected pediatric patients weighing at least 14 kg",
        )

    def test_use_peds_pattern(self):
        text = "Use of BIKTARVY in pediatric patients weighing at least 14 kg is supported by trials."
        self.assertEqual(
            fda_approvals.extract_short_indication(text),
            "pediatric patients weighing at least 14 kg",
        )

    def test_provides_for_pattern(self):
        text = "This supplement provides for the following changes for the treatment of HIV-1 infection."
        self.assertEqual(
            fda_approvals.extract_short_indication(text),
            "HIV-1 infection",
        )

    def test_name_in_supported_pattern(self):
        text = "Use of COSENTYX in pediatric patients with plaque psoriasis is supported by data."
        self.assertEqual(
            fda_approvals.extract_short_indication(text, brand_name="COSENTYX"),
            "pediatric patients with plaque psoriasis",
        )

    def test_name_antagonist_pattern(self):
        text = "DRUG is a monoclonal antibody indicated for the treatment of migraine."
        self.assertEqual(
            fda_approvals.extract_short_indication(text, brand_name="DRUG"),
            "migraine",
        )

    def test_indicated_for_colon_list(self):
        text = "indicated for the treatment of patients with: severe plaque psoriasis. (1.1) More stuff. A"
        self.assertEqual(
            fda_approvals.extract_short_indication(text),
            "patients with: severe plaque psoriasis",
        )

    def test_indicated_to_reduce_pattern(self):
        text = "indicated to reduce the risk of cardiovascular events."
        self.assertEqual(
            fda_approvals.extract_short_indication(text),
            "the risk of cardiovascular events",
        )


# ---------------------------------------------------------------------------
# fetch_suppl_approvals
# ---------------------------------------------------------------------------

class TestFetchSupplApprovals(unittest.TestCase):
    @patch('fda_approvals._fetch_paginated_results')
    def test_filters_and_builds_drugs(self, mock_fetch):
        valid = {
            "application_number": "NDA001",
            "openfda": {"brand_name": ["DrugA"], "generic_name": ["GenA"]},
            "products": [{"marketing_status": "Prescription", "brand_name": "DrugA",
                          "active_ingredients": [{"name": "ing", "strength": "10mg"}],
                          "dosage_form": "TABLET", "route": "ORAL"}],
            "submissions": [
                {
                    "submission_type": "SUPPL",
                    "submission_status": "AP",
                    "submission_class_code": "EFFICACY",
                    "submission_status_date": "20230115",
                    "submission_number": "1",
                    "review_priority": "PRIORITY",
                    "application_docs": [{"type": "Letter", "url": "http://x"}],
                }
            ],
        }
        mock_fetch.return_value = [valid]

        date_from = datetime(2023, 1, 1)
        date_to = datetime(2023, 1, 31)
        result = fda_approvals.fetch_suppl_approvals(date_from, date_to)

        self.assertEqual(len(result), 1)
        drug = result[0]
        self.assertEqual(drug["brand_name"], "DrugA")
        self.assertEqual(drug["submission_type"], "SUPPL")
        self.assertEqual(drug["type_badge"], "New Indication")
        self.assertEqual(drug["approval_date"], "2023-01-15")
        self.assertEqual(drug["slug"], "druga")

    @patch('fda_approvals._fetch_paginated_results')
    def test_skips_non_prescription(self, mock_fetch):
        entry = {
            "application_number": "NDA002",
            "openfda": {"brand_name": ["DrugB"]},
            "products": [{"marketing_status": "Over-the-counter"}],
            "submissions": [
                {"submission_type": "SUPPL", "submission_status": "AP",
                 "submission_class_code": "EFFICACY", "submission_status_date": "20230115"}
            ],
        }
        mock_fetch.return_value = [entry]
        result = fda_approvals.fetch_suppl_approvals(datetime(2023, 1, 1), datetime(2023, 1, 31))
        self.assertEqual(len(result), 0)

    @patch('fda_approvals._fetch_paginated_results')
    def test_skips_no_names(self, mock_fetch):
        entry = {
            "application_number": "NDA003",
            "openfda": {},
            "products": [{"marketing_status": "Prescription"}],
            "submissions": [
                {"submission_type": "SUPPL", "submission_status": "AP",
                 "submission_class_code": "EFFICACY", "submission_status_date": "20230115"}
            ],
        }
        mock_fetch.return_value = [entry]
        result = fda_approvals.fetch_suppl_approvals(datetime(2023, 1, 1), datetime(2023, 1, 31))
        self.assertEqual(len(result), 0)

    @patch('fda_approvals._fetch_paginated_results')
    def test_skips_non_efficacy_code(self, mock_fetch):
        entry = {
            "application_number": "NDA004",
            "openfda": {"brand_name": ["DrugD"]},
            "products": [{"marketing_status": "Prescription"}],
            "submissions": [
                {"submission_type": "SUPPL", "submission_status": "AP",
                 "submission_class_code": "LABEL", "submission_status_date": "20230115"}
            ],
        }
        mock_fetch.return_value = [entry]
        result = fda_approvals.fetch_suppl_approvals(datetime(2023, 1, 1), datetime(2023, 1, 31))
        self.assertEqual(len(result), 0)

    @patch('fda_approvals._fetch_paginated_results')
    def test_skips_non_AP_status(self, mock_fetch):
        entry = {
            "application_number": "NDA005",
            "openfda": {"brand_name": ["DrugE"]},
            "products": [{"marketing_status": "Prescription"}],
            "submissions": [
                {"submission_type": "SUPPL", "submission_status": "IP",
                 "submission_class_code": "EFFICACY", "submission_status_date": "20230115"}
            ],
        }
        mock_fetch.return_value = [entry]
        result = fda_approvals.fetch_suppl_approvals(datetime(2023, 1, 1), datetime(2023, 1, 31))
        self.assertEqual(len(result), 0)

    @patch('fda_approvals._fetch_paginated_results')
    def test_skips_date_out_of_range(self, mock_fetch):
        entry = {
            "application_number": "NDA006",
            "openfda": {"brand_name": ["DrugF"]},
            "products": [{"marketing_status": "Prescription"}],
            "submissions": [
                {"submission_type": "SUPPL", "submission_status": "AP",
                 "submission_class_code": "EFFICACY", "submission_status_date": "20221231"}
            ],
        }
        mock_fetch.return_value = [entry]
        result = fda_approvals.fetch_suppl_approvals(datetime(2023, 1, 1), datetime(2023, 1, 31))
        self.assertEqual(len(result), 0)

    @patch('fda_approvals._fetch_paginated_results')
    def test_skips_invalid_date_length(self, mock_fetch):
        entry = {
            "application_number": "NDA007",
            "openfda": {"brand_name": ["DrugG"]},
            "products": [{"marketing_status": "Prescription"}],
            "submissions": [
                {"submission_type": "SUPPL", "submission_status": "AP",
                 "submission_class_code": "EFFICACY", "submission_status_date": "2023"}
            ],
        }
        mock_fetch.return_value = [entry]
        result = fda_approvals.fetch_suppl_approvals(datetime(2023, 1, 1), datetime(2023, 1, 31))
        self.assertEqual(len(result), 0)

    @patch('fda_approvals._fetch_paginated_results')
    def test_dedup_key(self, mock_fetch):
        entry = {
            "application_number": "NDA008",
            "openfda": {"brand_name": ["DrugH"]},
            "products": [{"marketing_status": "Prescription"}],
            "submissions": [
                {"submission_type": "SUPPL", "submission_status": "AP",
                 "submission_class_code": "EFFICACY", "submission_status_date": "20230115",
                 "submission_number": "1"},
                {"submission_type": "SUPPL", "submission_status": "AP",
                 "submission_class_code": "EFFICACY", "submission_status_date": "20230115",
                 "submission_number": "1"},
            ],
        }
        mock_fetch.return_value = [entry]
        result = fda_approvals.fetch_suppl_approvals(datetime(2023, 1, 1), datetime(2023, 1, 31))
        self.assertEqual(len(result), 1)

    @patch('fda_approvals._fetch_paginated_results')
    def test_marketing_status_1(self, mock_fetch):
        entry = {
            "application_number": "NDA009",
            "openfda": {"brand_name": ["DrugI"]},
            "products": [{"marketing_status": "1"}],
            "submissions": [
                {"submission_type": "SUPPL", "submission_status": "AP",
                 "submission_class_code": "EFFICACY", "submission_status_date": "20230115"}
            ],
        }
        mock_fetch.return_value = [entry]
        result = fda_approvals.fetch_suppl_approvals(datetime(2023, 1, 1), datetime(2023, 1, 31))
        self.assertEqual(len(result), 1)


# ---------------------------------------------------------------------------
# fetch_pdf_text
# ---------------------------------------------------------------------------

class TestFetchPdfText(unittest.TestCase):
    @patch('fda_approvals.shutil.which', return_value=None)
    def test_empty_url_returns_empty(self, mock_which):
        self.assertEqual(fda_approvals.fetch_pdf_text(""), "")

    @patch('fda_approvals.subprocess.run')
    @patch('fda_approvals.urlopen')
    @patch('fda_approvals.shutil.which', return_value="/usr/bin/pdftotext")
    def test_success(self, mock_which, mock_urlopen, mock_run):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"fake pdf"
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_cm

        mock_run.return_value = MagicMock(returncode=0, stdout="extracted  pdf  text ", stderr="")
        result = fda_approvals.fetch_pdf_text("https://example.com/test.pdf")
        self.assertEqual(result, "extracted pdf text")

    @patch('fda_approvals.subprocess.run')
    @patch('fda_approvals.urlopen')
    @patch('fda_approvals.shutil.which', return_value="/usr/bin/pdftotext")
    def test_max_chars_truncation(self, mock_which, mock_urlopen, mock_run):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"fake pdf"
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_cm

        long_text = "x" * 10000
        mock_run.return_value = MagicMock(returncode=0, stdout=long_text, stderr="")
        result = fda_approvals.fetch_pdf_text("https://example.com/test.pdf", max_chars=100)
        self.assertEqual(len(result), 100)

    @patch('fda_approvals.urlopen')
    @patch('fda_approvals.shutil.which', return_value="/usr/bin/pdftotext")
    def test_urlopen_exception_returns_empty(self, mock_which, mock_urlopen):
        mock_urlopen.side_effect = URLError("network error")
        result = fda_approvals.fetch_pdf_text("https://example.com/test.pdf")
        self.assertEqual(result, "")

    @patch('fda_approvals.subprocess.run', side_effect=subprocess.TimeoutExpired("cmd", 30))
    @patch('fda_approvals.urlopen')
    @patch('fda_approvals.shutil.which', return_value="/usr/bin/pdftotext")
    def test_subprocess_exception_returns_empty(self, mock_which, mock_urlopen, mock_run):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"fake pdf"
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_cm
        result = fda_approvals.fetch_pdf_text("https://example.com/test.pdf")
        self.assertEqual(result, "")


# ---------------------------------------------------------------------------
# extract_new_indication_text
# ---------------------------------------------------------------------------

class TestExtractNewIndicationText(unittest.TestCase):
    def test_empty_text(self):
        self.assertEqual(fda_approvals.extract_new_indication_text(""), "")

    def test_none_text(self):
        self.assertEqual(fda_approvals.extract_new_indication_text(None), "")

    def test_approved_for_treatment_pattern(self):
        text = "This drug is approved for the treatment of severe plaque psoriasis."
        result = fda_approvals.extract_new_indication_text(text)
        self.assertIn("severe plaque psoriasis", result)

    def test_no_match_returns_empty(self):
        text = "This is just some random text with no relevant patterns at all."
        result = fda_approvals.extract_new_indication_text(text)
        self.assertEqual(result, "")

    def test_truncation_at_1200_chars(self):
        text = "This application provides for the following changes: " + "x" * 2000
        result = fda_approvals.extract_new_indication_text(text)
        self.assertLessEqual(len(result), 1200)


# ---------------------------------------------------------------------------
# fetch_new_indication_text
# ---------------------------------------------------------------------------

class TestFetchNewIndicationText(unittest.TestCase):
    def test_non_suppl_returns_empty(self):
        drug = {"submission_type": "ORIG"}
        self.assertEqual(fda_approvals.fetch_new_indication_text(drug), "")

    @patch('fda_approvals.fetch_pdf_text', return_value="")
    def test_no_letter_url_returns_empty(self, mock_pdf):
        drug = {"submission_type": "SUPPL", "application_docs": []}
        self.assertEqual(fda_approvals.fetch_new_indication_text(drug), "")

    @patch('fda_approvals.extract_new_indication_text', return_value="extracted text")
    @patch('fda_approvals.fetch_pdf_text', return_value="raw pdf text")
    def test_returns_extracted_text(self, mock_pdf, mock_extract):
        drug = {
            "submission_type": "SUPPL",
            "application_docs": [{"type": "Letter", "url": "http://example.com/letter.pdf"}],
        }
        result = fda_approvals.fetch_new_indication_text(drug)
        self.assertEqual(result, "extracted text")


# ---------------------------------------------------------------------------
# fetch_label — success path and other error paths
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

class TestProcessDrugLabel(unittest.TestCase):
    @patch('fda_approvals.fetch_new_indication_text', return_value="new indication")
    @patch('fda_approvals.fetch_label')
    def test_suppl_not_cached_fetches_label_and_new_indication(self, mock_fetch_label, mock_fetch_new):
        mock_fetch_label.return_value = {"indications_and_usage": ["drug is indicated for treatment of disease."]}
        drug = {
            "brand_name": "DRUG",
            "application_number": "NDA123",
            "submission_type": "SUPPL",
        }
        result = fda_approvals._process_drug_label((1, drug, 1, False, {}))
        self.assertEqual(result["submission_type"], "SUPPL")
        self.assertEqual(result["new_indication_text"], "new indication")
        # SUPPL with label: indication_source_text returns new_indication_text -> "new indication"
        self.assertEqual(result["indication_preview"], "new indication")

    @patch('fda_approvals.fetch_new_indication_text', return_value="indicated for treatment of psoriasis.")
    @patch('fda_approvals.fetch_label', return_value=None)
    def test_suppl_no_label_uses_new_indication_text(self, mock_fetch_label, mock_fetch_new):
        # In the no-cache/no-label branch, _process_drug_label overwrites
        # drug["new_indication_text"] with the return of fetch_new_indication_text,
        # then uses that as the source for extract_short_indication.
        drug = {
            "brand_name": "DRUG",
            "application_number": "NDA123",
            "submission_type": "SUPPL",
            "new_indication_text": "indicated for treatment of psoriasis.",
        }
        result = fda_approvals._process_drug_label((1, drug, 1, False, {}))
        self.assertIsNone(result["label"])
        # No label + SUPPL: indication_preview from new_indication_text (fetched value)
        # "indicated for treatment of psoriasis." -> extract_short_indication -> "psoriasis"
        self.assertEqual(result["indication_preview"], "psoriasis")

    @patch('fda_approvals.fetch_label', return_value=None)
    def test_orig_no_label_extracts_from_new_indication_text(self, mock_fetch_label):
        drug = {
            "brand_name": "DRUG",
            "application_number": "NDA123",
            "submission_type": "ORIG",
            "new_indication_text": "indicated for treatment of arthritis.",
        }
        result = fda_approvals._process_drug_label((1, drug, 1, False, {}))
        self.assertIsNone(result["label"])
        # ORIG no label: extract_short_indication from new_indication_text
        self.assertEqual(result["indication_preview"], "arthritis")

    @patch('fda_approvals.fetch_label')
    def test_orig_with_label(self, mock_fetch_label):
        mock_fetch_label.return_value = {"indications_and_usage": ["indicated for treatment of migraine."]}
        drug = {
            "brand_name": "DRUG",
            "application_number": "NDA123",
            "submission_type": "ORIG",
        }
        result = fda_approvals._process_drug_label((1, drug, 1, False, {}))
        self.assertEqual(result["indication_preview"], "migraine")

    @patch('fda_approvals.fetch_new_indication_text', return_value="new text")
    @patch('fda_approvals.fetch_label')
    def test_cached_suppl_with_new_indication_in_cache(self, mock_fetch_label, mock_fetch_new):
        """Cached event with new_indication_text should reuse it (not fetch)."""
        drug = {
            "brand_name": "DRUG",
            "application_number": "NDA123",
            "submission_type": "SUPPL",
            "submission_number": "1",
            "approval_date": "2026-01-01",
        }
        previous_data = {
            "NDA123:SUPPL:1:2026-01-01": {
                "label": {"indications_and_usage": ["cached indication text"]},
                "new_indication_text": "cached new indication",
            }
        }
        result = fda_approvals._process_drug_label((1, drug, 1, True, previous_data))
        # Should reuse cached label and cached new_indication_text
        self.assertEqual(result["label"]["indications_and_usage"], ["cached indication text"])
        self.assertEqual(result["new_indication_text"], "cached new indication")
        # Should NOT have called fetch_label or fetch_new_indication_text
        mock_fetch_label.assert_not_called()
        mock_fetch_new.assert_not_called()

    @patch('fda_approvals.fetch_new_indication_text', return_value="fetched new")
    @patch('fda_approvals.fetch_label')
    def test_cached_suppl_without_new_indication_fetches_it(self, mock_fetch_label, mock_fetch_new):
        """Cached event with label but no new_indication_text, SUPPL -> fetch new_indication_text."""
        drug = {
            "brand_name": "DRUG",
            "application_number": "NDA123",
            "submission_type": "SUPPL",
            "submission_number": "1",
            "approval_date": "2026-01-01",
        }
        previous_data = {
            "NDA123:SUPPL:1:2026-01-01": {
                "label": {"indications_and_usage": ["cached indication text"]},
            }
        }
        result = fda_approvals._process_drug_label((1, drug, 1, True, previous_data))
        self.assertEqual(result["new_indication_text"], "fetched new")
        mock_fetch_new.assert_called_once()

    @patch('fda_approvals.fetch_label')
    def test_cached_app_number_only(self, mock_fetch_label):
        """Cache hit via application_number only (no event key match)."""
        drug = {
            "brand_name": "DRUG",
            "application_number": "NDA123",
            "submission_type": "ORIG",
        }
        previous_data = {
            "NDA123": {
                "label": {"indications_and_usage": ["cached via app num"]},
            }
        }
        result = fda_approvals._process_drug_label((1, drug, 1, True, previous_data))
        self.assertEqual(result["label"]["indications_and_usage"], ["cached via app num"])
        mock_fetch_label.assert_not_called()

    @patch('fda_approvals.fetch_label')
    def test_cached_indication_preview_non_condition_emptied(self, mock_fetch_label):
        """Cached label where extracted indication is non-condition -> emptied."""
        drug = {
            "brand_name": "DRUG",
            "application_number": "NDA123",
            "submission_type": "ORIG",
        }
        previous_data = {
            "NDA123": {
                "label": {"indications_and_usage": ["efficacy"]},
            }
        }
        result = fda_approvals._process_drug_label((1, drug, 1, True, previous_data))
        # "efficacy" is a non-condition indication -> emptied
        self.assertEqual(result["indication_preview"], "")

    def test_non_cached_non_condition_preview_emptied(self):
        """When label fetched and indication_preview is non-condition, it gets emptied."""
        drug = {
            "brand_name": "DRUG",
            "application_number": "NDA123",
            "submission_type": "ORIG",
        }
        with patch('fda_approvals.fetch_label', return_value={"indications_and_usage": ["suppl"]}):
            result = fda_approvals._process_drug_label((1, drug, 1, False, {}))
        self.assertEqual(result["indication_preview"], "")

    def test_non_cached_no_label_non_condition_preview_emptied(self):
        """When no label and new_indication_text is non-condition, preview emptied."""
        drug = {
            "brand_name": "DRUG",
            "application_number": "NDA123",
            "submission_type": "ORIG",
            "new_indication_text": "orig",
        }
        with patch('fda_approvals.fetch_label', return_value=None):
            result = fda_approvals._process_drug_label((1, drug, 1, False, {}))
        self.assertEqual(result["indication_preview"], "")


# ---------------------------------------------------------------------------
# fetch_all_approvals
# ---------------------------------------------------------------------------

class TestFetchAllApprovals(unittest.TestCase):
    @patch('fda_approvals.fetch_drugsfda_approvals')
    def test_nme_type(self, mock_fetch):
        mock_fetch.return_value = [{"application_number": "NDA001"}]
        args = MagicMock()
        args.submission_type = "nme"
        args.date_from = "2026-01-01"
        args.date_to = "2026-01-31"
        args.limit = 100

        with patch('sys.stderr', new_callable=io.StringIO):
            result = fda_approvals.fetch_all_approvals(args, datetime(2026, 1, 1), datetime(2026, 1, 31))
        self.assertEqual(len(result), 1)
        mock_fetch.assert_called_once()

    @patch('fda_approvals.fetch_suppl_approvals')
    def test_suppl_type(self, mock_fetch):
        mock_fetch.return_value = [{"application_number": "NDA002"}]
        args = MagicMock()
        args.submission_type = "suppl"
        args.date_from = "2026-01-01"
        args.date_to = "2026-01-31"
        args.limit = 100

        with patch('sys.stderr', new_callable=io.StringIO):
            result = fda_approvals.fetch_all_approvals(args, datetime(2026, 1, 1), datetime(2026, 1, 31))
        self.assertEqual(len(result), 1)
        mock_fetch.assert_called_once()

    @patch('fda_approvals.fetch_suppl_approvals', return_value=[{"application_number": "NDA003", "approval_date": "2026-01-15", "type_badge": "New Indication"}])
    @patch('fda_approvals.fetch_drugsfda_approvals')
    def test_all_type_dedup(self, mock_fetch_orig, mock_fetch_suppl):
        # Return duplicate drugs to test dedup
        mock_fetch_orig.return_value = [
            {"application_number": "NDA001", "approval_date": "2026-01-10", "type_badge": "New Drug"},
            {"application_number": "NDA001", "approval_date": "2026-01-10", "type_badge": "New Drug"},  # dup
        ]
        args = MagicMock()
        args.submission_type = "all"
        args.date_from = "2026-01-01"
        args.date_to = "2026-01-31"
        args.limit = 100

        with patch('sys.stderr', new_callable=io.StringIO):
            result = fda_approvals.fetch_all_approvals(args, datetime(2026, 1, 1), datetime(2026, 1, 31))
        # 1 unique orig + 1 suppl = 2
        self.assertEqual(len(result), 2)


# ---------------------------------------------------------------------------
# process_labels — with cache and fetch
# ---------------------------------------------------------------------------

class TestProcessLabelsWithCache(unittest.TestCase):
    @patch('fda_approvals.save_label_cache')
    @patch('fda_approvals.load_previous_approvals', return_value={"NDA001": {"label": {"set_id": "x"}}})
    @patch('fda_approvals._process_drug_label')
    def test_cache_path(self, mock_process, mock_load_prev, mock_save):
        mock_process.side_effect = lambda info: info[1]  # return drug unchanged
        args = MagicMock()
        args.skip_labels = False
        args.cache = True

        drugs = [{"application_number": "NDA001", "brand_name": "A"}]
        with patch('sys.stderr', new_callable=io.StringIO):
            result = fda_approvals.process_labels(args, drugs)
        self.assertEqual(len(result), 1)
        mock_load_prev.assert_called_once()
        mock_save.assert_called_once()

    @patch('fda_approvals._process_drug_label')
    def test_no_cache_no_skip(self, mock_process):
        mock_process.side_effect = lambda info: info[1]
        args = MagicMock()
        args.skip_labels = False
        args.cache = False

        drugs = [{"application_number": "NDA001", "brand_name": "A"}]
        with patch('sys.stderr', new_callable=io.StringIO):
            result = fda_approvals.process_labels(args, drugs)
        self.assertEqual(len(result), 1)

    def test_skip_labels_sets_none_and_preview(self):
        args = MagicMock()
        args.skip_labels = True
        args.cache = False

        drugs = [
            {"application_number": "NDA001", "submission_class": "Type 1 - NME", "submission_type": "ORIG"},
            {"application_number": "NDA002", "submission_type": "SUPPL"},
        ]
        with patch('sys.stderr', new_callable=io.StringIO):
            result = fda_approvals.process_labels(args, drugs)
        self.assertIsNone(result[0]["label"])
        self.assertEqual(result[0]["indication_preview"], "Type 1 - NME")
        self.assertEqual(result[1]["indication_preview"], "SUPPL")


# ---------------------------------------------------------------------------
# summarize_indications
# ---------------------------------------------------------------------------

class TestSummarizeIndications(unittest.TestCase):
    def test_no_api_key_skips(self):
        args = MagicMock()
        args.summarize = True
        drugs = [{"application_number": "NDA001"}]
        with patch('sys.stderr', new_callable=io.StringIO):
            fda_approvals.summarize_indications(args, drugs, "")
        # Should not set indication_summary
        self.assertNotIn("indication_summary", drugs[0])

    @patch('fda_approvals.save_indication_summaries')
    @patch('fda_approvals.load_indication_summaries', return_value={})
    @patch('fda_approvals.summarize_indications_batch')
    def test_with_api_key(self, mock_batch, mock_load, mock_save):
        args = MagicMock()
        args.summarize = True
        drugs = [{"application_number": "NDA001", "indication_summary": "psoriasis"}]
        with patch('sys.stderr', new_callable=io.StringIO):
            fda_approvals.summarize_indications(args, drugs, "test_key")
        mock_batch.assert_called_once()
        mock_save.assert_called_once()

    def test_summarize_flag_false_does_nothing(self):
        args = MagicMock()
        args.summarize = False
        drugs = [{"application_number": "NDA001"}]
        # Should not call anything or modify drugs
        fda_approvals.summarize_indications(args, drugs, "key")
        self.assertNotIn("indication_summary", drugs[0])


# ---------------------------------------------------------------------------
# summarize_indications_batch — success path
# ---------------------------------------------------------------------------

class TestSummarizeIndicationsBatchSuccess(unittest.TestCase):
    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_success_path(self, mock_urlopen, mock_sleep):
        """LLM API success should populate summaries_cache and drug indication_summary."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{"message": {"content": "NDA123|psoriasis\nNDA456|migraine"}}]
        }).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_cm

        drugs = [
            {"application_number": "NDA123", "brand_name": "DrugA",
             "label": {"indications_and_usage": ["indicated for treatment of psoriasis"]}},
            {"application_number": "NDA456", "brand_name": "DrugB",
             "label": {"indications_and_usage": ["indicated for treatment of migraine"]}},
        ]
        summaries_cache = {}
        with patch('sys.stderr', new_callable=io.StringIO):
            fda_approvals.summarize_indications_batch(drugs, "key", summaries_cache)

        self.assertEqual(summaries_cache["NDA123"], "psoriasis")
        self.assertEqual(summaries_cache["NDA456"], "migraine")
        self.assertEqual(drugs[0]["indication_summary"], "psoriasis")
        self.assertEqual(drugs[1]["indication_summary"], "migraine")

    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_success_with_duplicate_cache_keys_in_response(self, mock_urlopen, mock_sleep):
        """Duplicate cache keys in LLM response should only set indication_summary once per key."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{"message": {"content": "NDA123|psoriasis\nNDA123|psoriasis"}}]
        }).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_cm

        drugs = [
            {"application_number": "NDA123", "brand_name": "DrugA",
             "label": {"indications_and_usage": ["indicated for treatment of psoriasis"]}},
        ]
        summaries_cache = {}
        with patch('sys.stderr', new_callable=io.StringIO):
            fda_approvals.summarize_indications_batch(drugs, "key", summaries_cache)

        self.assertEqual(drugs[0]["indication_summary"], "psoriasis")

    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_success_skips_non_condition_conditions(self, mock_urlopen, mock_sleep):
        """LLM response lines with non-condition conditions should be skipped."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{"message": {"content": "NDA123|efficacy"}}]
        }).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_cm

        drugs = [
            {"application_number": "NDA123", "brand_name": "DrugA",
             "label": {"indications_and_usage": ["some text"]}},
        ]
        summaries_cache = {}
        with patch('sys.stderr', new_callable=io.StringIO):
            fda_approvals.summarize_indications_batch(drugs, "key", summaries_cache)

        self.assertNotIn("NDA123", summaries_cache)

    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_success_skips_empty_or_pipeless_lines(self, mock_urlopen, mock_sleep):
        """Lines without '|' or with empty conditions should be skipped."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{"message": {"content": "no pipe here\nNDA123|\n|empty_key\nNDA456|migraine"}}]
        }).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_cm

        drugs = [
            {"application_number": "NDA456", "brand_name": "DrugB",
             "label": {"indications_and_usage": ["text"]}},
        ]
        summaries_cache = {}
        with patch('sys.stderr', new_callable=io.StringIO):
            fda_approvals.summarize_indications_batch(drugs, "key", summaries_cache)

        self.assertEqual(summaries_cache.get("NDA456"), "migraine")
        self.assertNotIn("", summaries_cache)

    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_cached_non_condition_reprocessed(self, mock_urlopen, mock_sleep):
        """Drugs with cached non-condition summaries should be reprocessed."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{"message": {"content": "NDA123:SUPPL:1:2026-01-01|arthritis"}}]
        }).encode()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_cm

        drugs = [
            {
                "application_number": "NDA123",
                "brand_name": "DrugA",
                "submission_type": "SUPPL",
                "submission_number": "1",
                "approval_date": "2026-01-01",
                "label": {"indications_and_usage": ["indicated for treatment of arthritis"]},
            }
        ]
        cache = {"NDA123:SUPPL:1:2026-01-01": "Efficacy"}  # non-condition
        with patch('sys.stderr', new_callable=io.StringIO):
            fda_approvals.summarize_indications_batch(drugs, "key", cache)

        self.assertEqual(drugs[0]["indication_summary"], "arthritis")

    def test_no_drugs_to_process_returns_early(self):
        """When all drugs have valid cached summaries, should return early."""
        drugs = [
            {"application_number": "NDA123", "label": {"indications_and_usage": ["text"]}},
        ]
        cache = {"NDA123": "psoriasis"}  # valid cached summary
        with patch('sys.stderr', new_callable=io.StringIO):
            fda_approvals.summarize_indications_batch(drugs, "key", cache)
        # Should not try to process (no urlopen call needed)
        self.assertEqual(drugs[0]["indication_summary"], "psoriasis")

    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_fallback_for_non_supplement_uses_brand(self, mock_urlopen, mock_sleep):
        """Fallback for non-supplement drugs should use brand_name."""
        mock_urlopen.side_effect = Exception("API error")
        drugs = [
            {"application_number": "NDA123", "brand_name": "DrugA",
             "label": {"indications_and_usage": ["text"]}},
        ]
        summaries_cache = {}
        with patch('sys.stderr', new_callable=io.StringIO):
            fda_approvals.summarize_indications_batch(drugs, "key", summaries_cache)
        self.assertEqual(summaries_cache["NDA123"], "DrugA")
        self.assertEqual(drugs[0]["indication_summary"], "DrugA")

    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_fallback_for_supplement_uses_extract_short(self, mock_urlopen, mock_sleep):
        """Fallback for supplement drugs should use extract_short_indication.

        The cache key for a SUPPL drug is application_number:submission_type:...,
        so it is "NDA123:SUPPL::" here (no submission_number/approval_date set).
        The source text for a SUPPL drug with a label is composed from
        indication_source_text, which prepends "Indications and Usage: " — so
        extract_short_indication returns the whole composed string, not just
        "arthritis".
        """
        mock_urlopen.side_effect = Exception("API error")
        drugs = [
            {
                "application_number": "NDA123",
                "brand_name": "DrugA",
                "submission_type": "SUPPL",
                "label": {"indications_and_usage": ["DrugA is indicated for treatment of arthritis"]},
            }
        ]
        summaries_cache = {}
        with patch('sys.stderr', new_callable=io.StringIO):
            fda_approvals.summarize_indications_batch(drugs, "key", summaries_cache)
        cache_key = "NDA123:SUPPL::"
        expected = fda_approvals.extract_short_indication(
            fda_approvals.indication_source_text(drugs[0]), brand_name="DrugA"
        )
        self.assertEqual(summaries_cache[cache_key], expected)
        self.assertEqual(drugs[0]["indication_summary"], expected)

    @patch('fda_approvals.time.sleep')
    @patch('fda_approvals.urlopen')
    def test_fallback_non_condition_emptied(self, mock_urlopen, mock_sleep):
        """Fallback that yields a non-condition indication should be emptied."""
        mock_urlopen.side_effect = Exception("API error")
        drugs = [
            {
                "application_number": "NDA123",
                "brand_name": "DrugA",
                "submission_type": "SUPPL",
                "label": {"indications_and_usage": ["efficacy"]},
            }
        ]
        summaries_cache = {}
        with patch('sys.stderr', new_callable=io.StringIO):
            fda_approvals.summarize_indications_batch(drugs, "key", summaries_cache)
        cache_key = "NDA123:SUPPL::"
        self.assertEqual(summaries_cache[cache_key], "")


# ---------------------------------------------------------------------------
# write_output — stdout path
# ---------------------------------------------------------------------------

class TestWriteOutputStdout(unittest.TestCase):
    def test_stdout_output(self):
        class Args:
            date_from = "2026-01-01"
            date_to = "2026-01-31"
            submission_type = "all"
            output = None

        drugs = [{"application_number": "NDA001"}]
        with patch('builtins.print') as mock_print:
            fda_approvals.write_output(Args, drugs)
        # Should print JSON to stdout
        mock_print.assert_called_once()
        printed = mock_print.call_args[0][0]
        data = json.loads(printed)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["query"]["date_from"], "2026-01-01")


# ---------------------------------------------------------------------------
# main() — full integration with mocks
# ---------------------------------------------------------------------------

class TestMain(unittest.TestCase):
    @patch('fda_approvals.write_output')
    @patch('fda_approvals.summarize_indications')
    @patch('fda_approvals.process_labels', side_effect=lambda args, drugs: drugs)
    @patch('fda_approvals.fetch_all_approvals')
    @patch('sys.argv', ['fda_approvals.py', '--from', '2026-01-01', '--to', '2026-01-31', '--skip-labels'])
    def test_main_skip_labels(self, mock_fetch, mock_process, mock_summarize, mock_write):
        mock_fetch.return_value = [{"application_number": "NDA001"}]
        with patch('sys.stderr', new_callable=io.StringIO):
            fda_approvals.main()
        mock_fetch.assert_called_once()
        mock_process.assert_called_once()
        mock_summarize.assert_called_once()
        mock_write.assert_called_once()


# ---------------------------------------------------------------------------
# write_text_atomic — OSError on write (not replace)
# ---------------------------------------------------------------------------

class TestWriteTextAtomicWriteFailure(unittest.TestCase):
    def test_write_failure_cleans_temp_and_raises(self):
        """If the write itself fails (temp file creation), should raise and clean up."""
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "output.txt")
        try:
            with patch('fda_approvals.tempfile.NamedTemporaryFile', side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    fda_approvals.write_text_atomic(path, "data")
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# fetch_drugsfda_approvals — submission_type filter and no-date edge
# ---------------------------------------------------------------------------

class TestFetchDrugsfdaApprovalsEdgeCases(unittest.TestCase):
    @patch('fda_approvals._fetch_paginated_results')
    def test_submission_type_filter(self, mock_fetch):
        """submission_type filter should be included in the search."""
        valid = {
            "application_number": "NDA001",
            "openfda": {"brand_name": ["Brand"], "generic_name": ["Gen"]},
            "submissions": [
                {"submission_type": "ORIG", "submission_status": "AP", "submission_status_date": "20230115"}
            ],
            "products": [{"marketing_status": "Prescription"}],
        }
        mock_fetch.return_value = [valid]
        with patch('sys.stderr', new_callable=io.StringIO):
            result = fda_approvals.fetch_drugsfda_approvals(
                datetime(2023, 1, 1), datetime(2023, 1, 31),
                submission_type="Type 1 - New Molecular Entity"
            )
        self.assertEqual(len(result), 1)

    @patch('fda_approvals._fetch_paginated_results')
    def test_approval_date_not_8_chars_uses_raw(self, mock_fetch):
        """When approval_date_raw is not 8 chars, it's used as-is without date filter."""
        valid = {
            "application_number": "NDA001",
            "openfda": {"brand_name": ["Brand"]},
            "submissions": [
                {"submission_type": "ORIG", "submission_status": "AP", "submission_status_date": "2023-01-15"}
            ],
            "products": [{"marketing_status": "Prescription"}],
        }
        mock_fetch.return_value = [valid]
        result = fda_approvals.fetch_drugsfda_approvals(datetime(2023, 1, 1), datetime(2023, 1, 31))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["approval_date"], "2023-01-15")

    @patch('fda_approvals._fetch_paginated_results')
    def test_generic_name_only_no_brand(self, mock_fetch):
        """Drug with only generic_name (no brand_name) should be included."""
        valid = {
            "application_number": "NDA001",
            "openfda": {"generic_name": ["GenOnly"]},
            "submissions": [
                {"submission_type": "ORIG", "submission_status": "AP", "submission_status_date": "20230115"}
            ],
            "products": [{"marketing_status": "Prescription"}],
        }
        mock_fetch.return_value = [valid]
        result = fda_approvals.fetch_drugsfda_approvals(datetime(2023, 1, 1), datetime(2023, 1, 31))
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]["brand_name"])
        self.assertEqual(result[0]["generic_name"], "GenOnly")


# ---------------------------------------------------------------------------
# Coverage for remaining missing lines: 160, 321, 347, 408-409, 650, 1120
# ---------------------------------------------------------------------------

class TestFetchJsonUnreachableRetry(unittest.TestCase):
    """Cover line 160: the unreachable RuntimeError at the end of fetch_json.

    The for-loop in fetch_json always either returns, raises, or continues, so
    line 160 is only reachable if max_retries == 0 (empty range => falls through).
    """
    @patch('fda_approvals.urlopen')
    def test_zero_retries_falls_through(self, mock_urlopen):
        # With max_retries=0 the for-loop body never executes, so execution
        # falls through to the unreachable RuntimeError.
        with self.assertRaises(RuntimeError):
            fda_approvals.fetch_json("http://example.com", max_retries=0)


class TestExtractShortIndicationIndTreatmentBranch(unittest.TestCase):
    """Cover line 321: the IND_TREATMENT_RE branch in extract_short_indication.

    This branch fires for 'indicated for the treatment of CONDITION.' when the
    earlier COLON_LIST_RE (which requires a colon-list) does not match.
    """
    def test_ind_treatment_branch(self):
        # COLON_LIST_RE has re.IGNORECASE so [A-Z] matches lowercase, making it
        # very permissive. The only way to reach IND_TREATMENT_RE is text where
        # COLON_LIST_RE's ending fails: period + space + digit (no open paren).
        result = fda_approvals.extract_short_indication(
            "is indicated for the treatment of plaque psoriasis. 5 patients experienced side effects",
            brand_name="",
        )
        self.assertEqual(result, "plaque psoriasis")


class TestExtractShortIndicationNameInSupportedBranch(unittest.TestCase):
    """Cover line 347: the get_name_in_supported_re branch.

    Pattern: 'DRUGNAME in CONDITION is supported' (used in FDA supplement
    approval letters). Requires brand_name to be set so clean_name is non-empty,
    and earlier patterns must not match.
    """
    def test_name_in_supported_branch(self):
        result = fda_approvals.extract_short_indication(
            "The safety and effectiveness of DrugX in patients with heart failure is supported by evidence.",
            brand_name="DrugX",
        )
        self.assertIn("heart failure", result)


class TestWriteTextAtomicUnlinkOSError(unittest.TestCase):
    """Cover lines 408-409: the except OSError: pass when unlinking the temp file.

    We force os.replace to fail (so the except Exception block runs), with a
    real temp file present (so tmp_path is set and exists), and make os.unlink
    raise OSError to hit the inner except.
    """
    def test_replace_fails_and_unlink_raises_oserror(self):
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "output.txt")
        try:
            real_ntf = fda_approvals.tempfile.NamedTemporaryFile
            real_replace = fda_approvals.os.replace
            real_unlink = fda_approvals.os.unlink

            def fake_replace(src, dst):
                raise OSError("replace failed")

            def fake_unlink(p):
                raise OSError("unlink failed")

            with patch('fda_approvals.os.replace', side_effect=fake_replace), \
                 patch('fda_approvals.os.unlink', side_effect=fake_unlink):
                with self.assertRaises(OSError):
                    fda_approvals.write_text_atomic(path, "data")
            # Ensure we used the real NamedTemporaryFile so a temp file exists
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestFetchSupplApprovalsSkipsNonSupplSubmission(unittest.TestCase):
    """Cover line 650: the continue when submission_type != 'SUPPL'.

    Provide an entry whose submissions list contains a non-SUPPL submission
    first (so the continue on line 650 fires) followed by a valid SUPPL
    submission, ensuring the drug is still picked up.
    """
    @patch('fda_approvals._fetch_paginated_results')
    def test_skips_non_suppl_then_processes_suppl(self, mock_fetch):
        entry = {
            "application_number": "NDA010",
            "openfda": {"brand_name": ["DrugJ"]},
            "products": [{"marketing_status": "Prescription"}],
            "submissions": [
                # Non-SUPPL submission first -> hits line 650 continue
                {"submission_type": "ORIG", "submission_status": "AP",
                 "submission_class_code": "EFFICACY", "submission_status_date": "20230115"},
                # Valid SUPPL submission -> should be processed
                {"submission_type": "SUPPL", "submission_status": "AP",
                 "submission_class_code": "EFFICACY", "submission_status_date": "20230115",
                 "submission_number": "1"},
            ],
        }
        mock_fetch.return_value = [entry]
        result = fda_approvals.fetch_suppl_approvals(
            datetime(2023, 1, 1), datetime(2023, 1, 31)
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["brand_name"], "DrugJ")


class TestMainEntryBlock(unittest.TestCase):
    """Cover line 1120: the 'if __name__ == \"__main__\": main()' block.

    Executing the module as a subprocess exercises this block.
    """
    def test_module_main_block_runs(self):
        # Run with --help so main() parses args and exits before doing work.
        proc = subprocess.run(
            [sys.executable, "fda_approvals.py", "--help"],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("usage:", proc.stdout.lower())


if __name__ == "__main__":
    unittest.main()