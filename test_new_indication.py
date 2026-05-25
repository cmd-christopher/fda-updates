import unittest
from unittest.mock import patch

import fda_approvals


class TestApprovalEventKey(unittest.TestCase):
    def test_original_uses_application_number(self):
        drug = {"application_number": "NDA123456", "submission_type": "ORIG"}
        self.assertEqual(fda_approvals.approval_event_key(drug), "NDA123456")

    def test_supplement_uses_event_identity(self):
        drug = {
            "application_number": "NDA123456",
            "submission_type": "SUPPL",
            "submission_number": "7",
            "approval_date": "2026-05-20",
        }
        self.assertEqual(fda_approvals.approval_event_key(drug), "NDA123456:SUPPL:7:2026-05-20")


class TestApplicationDocs(unittest.TestCase):
    def test_get_application_doc_url(self):
        drug = {
            "application_docs": [
                {"type": "Label", "url": "https://example.test/label.pdf"},
                {"type": "Letter", "url": "https://example.test/letter.pdf"},
            ]
        }
        self.assertEqual(fda_approvals.get_application_doc_url(drug, "Letter"), "https://example.test/letter.pdf")

    def test_missing_application_doc_url(self):
        self.assertEqual(fda_approvals.get_application_doc_url({"application_docs": []}, "Letter"), "")


class TestExtractNewIndicationText(unittest.TestCase):
    def test_extracts_changes_from_approval_letter(self):
        text = """
        This Prior Approval supplemental new drug application provides for the following
        changes to the Prescribing Information and Patient Information:
        To expand the patient population for Biktarvy to include HIV-1 infected pediatric
        patients weighing at least 14 kg. This change is supported by data.
        APPROVAL & LABELING We have completed our review.
        """
        result = fda_approvals.extract_new_indication_text(text)
        self.assertIn("HIV-1 infected pediatric", result)
        self.assertNotIn("APPROVAL", result)

    def test_extracts_section_change_from_approval_letter(self):
        text = """
        It is approved, effective on the date of this letter, for use as recommended
        in the enclosed agreed-upon labeling with a minor editorial revision listed below.
        Section 8.4 Pediatric Use Use of BIKTARVY in pediatric patients weighing at
        least 14 kg is supported by trials in adults.
        CONTENT OF LABELING As soon as possible...
        """
        result = fda_approvals.extract_new_indication_text(text)
        self.assertIn("BIKTARVY in pediatric patients weighing at least 14 kg", result)
        self.assertNotIn("enclosed agreed-upon labeling", result)

    def test_extract_short_indication_from_expansion_text(self):
        text = "To expand the patient population for Biktarvy to include HIV-1 infected pediatric patients weighing at least 14 kg."
        self.assertEqual(
            fda_approvals.extract_short_indication(text, brand_name="Biktarvy"),
            "HIV-1 infected pediatric patients weighing at least 14 kg",
        )


class TestSupplementPreview(unittest.TestCase):
    @patch("fda_approvals.fetch_new_indication_text", return_value="")
    @patch("fda_approvals.fetch_label")
    def test_supplement_without_new_text_does_not_use_full_label_indication(self, mock_fetch_label, mock_fetch_new):
        mock_fetch_label.return_value = {
            "indications_and_usage": ["DRUG is indicated for the treatment of old disease."]
        }
        drug = {
            "brand_name": "DRUG",
            "application_number": "NDA123456",
            "submission_type": "SUPPL",
            "submission_class": "Efficacy",
            "type_badge": "New Indication",
        }

        result = fda_approvals._process_drug_label((1, drug, 1, False, {}))

        self.assertEqual(result["indication_preview"], "old disease")

    @patch("fda_approvals.time.sleep")
    @patch("fda_approvals.urlopen", side_effect=Exception("mocked"))
    def test_non_condition_summary_cache_is_reprocessed(self, mock_urlopen, mock_sleep):
        drugs = [
            {
                "brand_name": "DRUG",
                "application_number": "NDA123456",
                "submission_type": "SUPPL",
                "submission_number": "1",
                "approval_date": "2026-01-01",
                "submission_class": "Efficacy",
                "label": {
                    "indications_and_usage": ["DRUG is indicated for the treatment of acute leukemia."]
                },
            }
        ]
        cache = {"NDA123456:SUPPL:1:2026-01-01": "Efficacy"}

        fda_approvals.summarize_indications_batch(drugs, "", cache)

        self.assertNotEqual(drugs[0].get("indication_summary"), "Efficacy")

    def test_efficacy_phrases_are_not_conditions(self):
        self.assertTrue(fda_approvals.is_non_condition_indication("Efficacy Update"))
        self.assertTrue(fda_approvals.is_non_condition_indication("Safety Efficacy Data"))


if __name__ == "__main__":
    unittest.main()
