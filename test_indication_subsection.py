"""Tests for choosing the model input of supplement approvals.

Label strings are trimmed copies of real openFDA labels (TECENTRIQ, GAZYVA,
AQNEURSA, KEYTRUDA QLEX, SOGROYA) and real FDA approval-letter wording.
"""
import inspect
import unittest
from unittest.mock import patch

import fda_approvals

TECENTRIQ_RMC = [
    "Indications and Usage ( 1.6 ) 05/2026 Indications and Usage ( 1.7 ) 10/2026 "
    "Dosage and Administration ( 2.4 ) 03/2026 Dosage and Administration ( 2.1 , 2.2 , 2.4 ) 05/2026 "
    "Dosage and Administration ( 2.1 , 2.2 ) 10/2026 Warnings and Precautions ( 5.1 ) 05/2026"
]
TECENTRIQ_IU = [
    "1 INDICATIONS AND USAGE TECENTRIQ is a programmed death-ligand 1 (PD-L1) blocking antibody indicated: "
    "Non-Small Cell Lung Cancer (NSCLC) as adjuvant treatment following resection and platinum-based "
    "chemotherapy for adult patients with stage II to IIIA NSCLC. ( 1.1 , 14.1 ) "
    "Muscle Invasive Bladder Cancer (MIBC) as adjuvant treatment of adult patients with MIBC. ( 1.6 ) "
    "Mismatch Repair–Deficient Colon Cancer in combination with a fluoropyrimidine and oxaliplatin, "
    "for Stage III dMMR colon cancer. ( 1.7 ) "
    "1.1 Non-Small Cell Lung Cancer TECENTRIQ, as a single agent, is indicated as adjuvant treatment "
    "following resection and platinum-based chemotherapy for adult patients with Stage II to IIIA NSCLC. "
    "1.6 Muscle Invasive Bladder Cancer TECENTRIQ, as a single agent, is indicated as adjuvant treatment "
    "of adult patients with muscle invasive bladder cancer (MIBC) after cystectomy [see Dosage and "
    "Administration (2.1) ] . "
    "1.7 Mismatch Repair–Deficient Colon Cancer TECENTRIQ, in combination with a fluoropyrimidine and "
    "oxaliplatin, is indicated for the adjuvant treatment of adult and pediatric patients 2 years of age "
    "and older with Stage III, mismatch repair deficient (dMMR) colon cancer."
]

GAZYVA_RMC = [
    "Indication and Usage, Lupus Nephritis ( 1.3 ) 10/2025 Indication and Usage, Childhood-Onset "
    "Idiopathic Nephrotic Syndrome ( 1.4 ) 9/2026 Dosage and Administration ( 2 ) 10/2025, 9/2026 "
    "Warnings and Precautions ( 5 ) 9/2026"
]
GAZYVA_IU = [
    "1 INDICATIONS AND USAGE GAZYVA is a CD20-directed cytolytic antibody indicated: in combination "
    "with chlorambucil, for previously untreated chronic lymphocytic leukemia (CLL). ( 1.1 , 14 ) "
    "for the treatment of adult patients with active lupus nephritis (LN) ( 1.3 , 14 ) "
    "to reduce the risk of relapse in patients with childhood-onset idiopathic nephrotic syndrome. ( 1.4 , 14 ) "
    "1.1 Chronic Lymphocytic Leukemia (CLL) GAZYVA, in combination with chlorambucil, is indicated for "
    "the treatment of patients with previously untreated chronic lymphocytic leukemia. "
    "1.3 Lupus Nephritis (LN) GAZYVA is indicated for the treatment of adult patients with active lupus "
    "nephritis who are receiving standard therapy. "
    "1.4 Childhood-Onset Idiopathic Nephrotic Syndrome (INS) GAZYVA is indicated to reduce the risk of "
    "relapse in adult and pediatric patients 2 years of age and older with childhood-onset idiopathic "
    "nephrotic syndrome who are in complete remission."
]

KEYTRUDA_QLEX_RMC = [
    "Indications and Usage ( 1 ) 10/2026 Dosage and Administration ( 2 ) 08/2026 "
    "Warnings and Precautions ( 5 ) 05/2026"
]
KEYTRUDA_QLEX_IU = [
    "1 INDICATIONS AND USAGE KEYTRUDA QLEX is indicated: Melanoma for the treatment of adult patients "
    "with unresectable or metastatic melanoma. ( 1.1 ) "
    "1.1 Melanoma KEYTRUDA QLEX is indicated for the treatment of adult patients with unresectable or "
    "metastatic melanoma. "
    "1.10 Tumor Mutational Burden-High Cancer KEYTRUDA QLEX is indicated for TMB-H solid tumors."
]


def supplement(approval_date, rmc, indications, **extra):
    drug = {
        "brand_name": "DRUG",
        "submission_type": "SUPPL",
        "approval_date": approval_date,
        "label": {"recent_major_changes": rmc, "indications_and_usage": indications},
    }
    drug.update(extra)
    return drug


class TestRecentMajorChangesEntries(unittest.TestCase):
    def entries(self, text):
        return fda_approvals.recent_major_changes_entries({"recent_major_changes": [text]})

    def test_subsections_and_dates(self):
        entries = self.entries(TECENTRIQ_RMC[0])
        self.assertEqual(entries[0], {"name": "Indications and Usage", "sections": ["1.6"], "dates": [(2026, 5)]})
        self.assertEqual(entries[1], {"name": "Indications and Usage", "sections": ["1.7"], "dates": [(2026, 10)]})
        self.assertEqual(entries[3]["sections"], ["2.1", "2.2", "2.4"])

    def test_named_entry_and_several_dates(self):
        entries = self.entries(GAZYVA_RMC[0])
        self.assertEqual(entries[1]["name"], "Indication and Usage, Childhood-Onset Idiopathic Nephrotic Syndrome")
        self.assertEqual(entries[1]["sections"], ["1.4"])
        self.assertEqual(entries[2]["dates"], [(2025, 10), (2026, 9)])

    def test_recent_major_changes_heading_is_dropped(self):
        entries = self.entries("RECENT MAJOR CHANGES SECTION Indications and Usage ( 1.1 , 1.2 ) 10/2026")
        self.assertEqual(entries, [{"name": "Indications and Usage", "sections": ["1.1", "1.2"], "dates": [(2026, 10)]}])

    def test_dotted_leaders_before_date(self):
        entries = self.entries("Indication and Usage ( 1 )………………….……2/2026 Dosage and Administration ( 2.1 , 2.3 )……….2/2026")
        self.assertEqual([e["dates"] for e in entries], [[(2026, 2)], [(2026, 2)]])
        self.assertEqual(entries[0]["sections"], ["1"])

    def test_entry_without_section_number(self):
        entries = self.entries("Boxed Warning 11/2026 Indications ( 1 ) 3/2025")
        self.assertEqual(entries[0], {"name": "Boxed Warning", "sections": [], "dates": [(2026, 11)]})
        self.assertTrue(fda_approvals.is_indications_entry(entries[1]))

    def test_missing_recent_major_changes(self):
        self.assertEqual(fda_approvals.recent_major_changes_entries({}), [])
        self.assertEqual(fda_approvals.recent_major_changes_entries(None), [])


class TestLabelSubsectionText(unittest.TestCase):
    def test_heading_not_reference(self):
        text = fda_approvals.label_subsection_text(TECENTRIQ_IU[0], "1.7")
        self.assertTrue(text.startswith("1.7 Mismatch Repair–Deficient Colon Cancer TECENTRIQ"))
        self.assertIn("Stage III, mismatch repair deficient (dMMR) colon cancer", text)

    def test_stops_at_next_heading(self):
        text = fda_approvals.label_subsection_text(TECENTRIQ_IU[0], "1.6")
        self.assertIn("muscle invasive bladder cancer", text)
        self.assertNotIn("colon", text)

    def test_one_does_not_match_ten(self):
        self.assertTrue(fda_approvals.label_subsection_text(KEYTRUDA_QLEX_IU[0], "1.1").startswith("1.1 Melanoma"))
        self.assertNotIn("TMB-H", fda_approvals.label_subsection_text(KEYTRUDA_QLEX_IU[0], "1.1"))
        self.assertIn("TMB-H", fda_approvals.label_subsection_text(KEYTRUDA_QLEX_IU[0], "1.10"))

    def test_includes_child_subsections(self):
        text = "1.1 Adults DRUG treats A. 1.1.1 Children DRUG treats B. 1.2 Other DRUG treats C."
        self.assertEqual(fda_approvals.label_subsection_text(text, "1.1"), "1.1 Adults DRUG treats A. 1.1.1 Children DRUG treats B.")

    def test_missing_subsection(self):
        self.assertEqual(fda_approvals.label_subsection_text(TECENTRIQ_IU[0], "1.9"), "")


class TestApprovedIndicationText(unittest.TestCase):
    def test_uses_subsection_dated_in_approval_month(self):
        drug = supplement("2026-10-08", TECENTRIQ_RMC, TECENTRIQ_IU)
        self.assertTrue(fda_approvals.approved_indication_text(drug).startswith("1.7 Mismatch Repair"))

    def test_older_supplement_of_same_label_uses_its_own_month(self):
        drug = supplement("2026-05-15", TECENTRIQ_RMC, TECENTRIQ_IU)
        self.assertTrue(fda_approvals.approved_indication_text(drug).startswith("1.6 Muscle Invasive Bladder Cancer"))

    def test_named_entry(self):
        drug = supplement("2026-09-25", GAZYVA_RMC, GAZYVA_IU)
        self.assertTrue(fda_approvals.approved_indication_text(drug).startswith("1.4 Childhood-Onset Idiopathic Nephrotic"))

    def test_no_entry_in_approval_month(self):
        drug = supplement("2026-11-13", GAZYVA_RMC, GAZYVA_IU)
        self.assertEqual(fda_approvals.approved_indication_text(drug), "")

    def test_several_subsections_are_joined(self):
        rmc = ["Indications and Usage ( 1.6 , 1.7 ) 10/2026"]
        text = fda_approvals.approved_indication_text(supplement("2026-10-08", rmc, TECENTRIQ_IU))
        self.assertIn("1.6 Muscle Invasive", text)
        self.assertIn("1.7 Mismatch Repair", text)

    def test_whole_section_with_several_indications_is_unknown(self):
        drug = supplement("2026-10-16", KEYTRUDA_QLEX_RMC, KEYTRUDA_QLEX_IU)
        self.assertEqual(fda_approvals.approved_indication_text(drug), "")

    def test_whole_section_with_single_indication(self):
        iu = ["1 INDICATIONS AND USAGE DRUG is indicated for the treatment of severe alopecia areata in adults."]
        drug = supplement("2026-09-25", ["Indications and Usage ( 1 ) 9/2026"], iu)
        self.assertEqual(fda_approvals.approved_indication_text(drug), "DRUG is indicated for the treatment of severe alopecia areata in adults.")

    def test_bad_approval_date(self):
        self.assertEqual(fda_approvals.approved_indication_text(supplement("", TECENTRIQ_RMC, TECENTRIQ_IU)), "")


class TestLabelingOnlySupplement(unittest.TestCase):
    def test_only_non_indication_changes_in_month(self):
        rmc = ["Indications and Usage ( 1.2 ) 4/2025 Warnings and Precautions, Uveitis ( 5.5 ) 6/2026"]
        self.assertTrue(fda_approvals.is_labeling_only_supplement(supplement("2026-06-03", rmc, [])))

    def test_indication_change_in_month(self):
        self.assertFalse(fda_approvals.is_labeling_only_supplement(supplement("2026-10-08", TECENTRIQ_RMC, TECENTRIQ_IU)))

    def test_nothing_dated_in_month_is_not_known(self):
        self.assertFalse(fda_approvals.is_labeling_only_supplement(supplement("2026-11-13", GAZYVA_RMC, GAZYVA_IU)))


class TestIndicationModelText(unittest.TestCase):
    def test_supplement_gets_approved_subsection_past_600_chars(self):
        drug = supplement("2026-10-08", TECENTRIQ_RMC, TECENTRIQ_IU)
        self.assertNotIn("Stage III, mismatch repair", fda_approvals.indication_source_text(drug)[:600])
        self.assertTrue(fda_approvals.indication_model_text(drug).startswith("1.7 Mismatch Repair"))

    def test_letter_text_wins(self):
        drug = supplement("2026-10-08", TECENTRIQ_RMC, TECENTRIQ_IU, new_indication_text="Stage III dMMR colon cancer")
        self.assertEqual(fda_approvals.indication_model_text(drug), "Stage III dMMR colon cancer")

    def test_falls_back_to_first_600_chars(self):
        drug = supplement("2026-11-13", GAZYVA_RMC, GAZYVA_IU)
        expected = fda_approvals.indication_source_text(drug)[:600]
        self.assertEqual(fda_approvals.indication_model_text(drug), expected)
        self.assertTrue(expected.startswith("Recent Major Changes:"))

    def test_original_approval_unchanged(self):
        drug = {"submission_type": "ORIG", "label": {"indications_and_usage": ["x" * 900]}}
        self.assertEqual(fda_approvals.indication_model_text(drug), "x" * 600)


class TestLetterWording(unittest.TestCase):
    """Approval-letter sentences the older pattern missed."""

    def extract(self, sentence):
        return fda_approvals.extract_new_indication_text(
            "Please refer to your supplemental biologics license application (sBLA) received May 15, 2026. "
            + sentence
            + " APPROVAL & LABELING We have completed our review of this application."
        )

    def test_sbla_provides_for(self):
        result = self.extract(
            "This Prior Approval sBLA provides for a new indication, the treatment of adult patients with "
            "primary membranous nephropathy at risk of disease progression."
        )
        self.assertTrue(result.startswith("a new indication, the treatment of adult patients with primary membranous nephropathy"))
        self.assertNotIn("APPROVAL", result)

    def test_application_provides_without_for(self):
        result = self.extract(
            "This Prior Approval supplemental biologics license application provides a new indication for "
            "Jemperli: for the treatment of adults with Stage II/III locally advanced rectal cancer."
        )
        self.assertIn("locally advanced rectal cancer", result)

    def test_sbla_adds_new_indication(self):
        result = self.extract(
            "This Prior Approval sBLA adds the following new indication: TECENTRIQ, in combination with a "
            "fluoropyrimidine and oxaliplatin, is indicated for Stage III, mismatch repair deficient (dMMR) colon cancer"
        )
        self.assertTrue(result.startswith("TECENTRIQ, in combination"))

    def test_snda_provides_for_use(self):
        result = self.extract(
            "This Prior Approval sNDA provides for use of Aqneursa as a treatment of ataxia in adults and "
            "pediatric patients with ataxia-telangiectasia weighing ≥ 15 kg."
        )
        self.assertTrue(result.startswith("use of Aqneursa as a treatment of ataxia"))

    def test_reference_to_sbla_is_not_a_match(self):
        self.assertEqual(
            fda_approvals.extract_new_indication_text("your supplemental application (sBLA) received May 15, 2026"),
            "",
        )


class TestLabelingOnlyLaterIndicationDate(unittest.TestCase):
    def test_later_indication_change_can_hide_this_months(self):
        # KEYTRUDA 2026-07-10 added an indication, but section 1 now shows only 10/2026.
        rmc = ["Indications and Usage ( 1 ) 10/2026 Dosage and Administration ( 2 ) 07/2026"]
        self.assertFalse(fda_approvals.is_labeling_only_supplement(supplement("2026-07-10", rmc, [])))

    def test_older_indication_date_does_not_block(self):
        rmc = ["Indications and Usage ( 1.2 ) 4/2025 Warnings and Precautions ( 5.5 ) 6/2026"]
        self.assertTrue(fda_approvals.is_labeling_only_supplement(supplement("2026-06-03", rmc, [])))


class TestLabelingOnlyLetter(unittest.TestCase):
    """Real approval-letter "provides for" texts."""

    LABELING = [
        "revisions based on the results from RA Safety Studies 1 and 2, to include the risk of thrombosis and malignancies with Olumiant in the Boxed Warning",
        "revisions to Section 2 (Dosage and Administration) and Section 14 (Clinical Studies) of the USPI to incorporate the final OS analysis of CAPItello-291",
        "update to the United States Prescribing Information (USPI) to incorporate final overall survival results from Study J2G-MC-JZJB",
        "pediatric labeling text pursuant to the Pediatric Research Equity Act (PREA). This approval is in response to a PREA PMR",
        "a new dosing regimen for Tevimbra (tislelizumab-jsgr) of 400 mg intravenous infusion once every 6 weeks",
        "the addition of the SCP-111 autoinjector drug/device combination product",
        "a new subcutaneous (SC) route of administration of mosunetuzumab-axgb for the treatment of adult patients with relapsed follicular lymphoma",
    ]
    INDICATION = [
        "a new indication, the treatment of adult patients with primary membranous nephropathy at risk of disease progression",
        "revision to the INDICATIONS AND USAGE section of the Prescribing Information to include postoperative pain as part of pain management",
        "the expansion of the pediatric age group for the indication of Xenoview from ages 12 years and older to ages 6 years and older",
        "pediatric labeling pursuant to BPCA. This supplemental application is approving use in pediatric patients ages 10 years and older",
        "revisions to the Xigduo XR Prescribing Information to reflect that the dapagliflozin component is indicated in adults with heart failure",
        "revisions to the prescribing information to add use for the treatment of edema in pediatric patients weighing 43 kg and greater",
        "the treatment of severe alopecia areata in adults and pediatric patients 12 years of age and older",
    ]

    def test_labeling_letters(self):
        for text in self.LABELING:
            with self.subTest(text=text[:40]):
                self.assertTrue(fda_approvals.is_labeling_only_letter(text))

    def test_indication_letters(self):
        for text in self.INDICATION:
            with self.subTest(text=text[:40]):
                self.assertFalse(fda_approvals.is_labeling_only_letter(text))

    def test_empty(self):
        self.assertFalse(fda_approvals.is_labeling_only_letter(""))


class TestIsLabelingUpdate(unittest.TestCase):
    LABEL_ONLY_RMC = ["Indications and Usage ( 1.2 ) 4/2025 Warnings and Precautions ( 5.5 ) 6/2026"]

    def test_letter_beats_label_saying_labeling_only(self):
        drug = supplement("2026-06-03", self.LABEL_ONLY_RMC, [],
                          new_indication_text="the addition of a new indication for treatment of diabetic retinopathy")
        self.assertFalse(fda_approvals.is_labeling_update(drug))

    def test_letter_beats_label_listing_indication_change(self):
        drug = supplement("2026-10-08", TECENTRIQ_RMC, TECENTRIQ_IU,
                          new_indication_text="revisions to Section 14 (Clinical Studies) of the USPI with final overall survival results")
        self.assertTrue(fda_approvals.is_labeling_update(drug))

    def test_label_decides_without_letter(self):
        self.assertTrue(fda_approvals.is_labeling_update(supplement("2026-06-03", self.LABEL_ONLY_RMC, [])))
        self.assertFalse(fda_approvals.is_labeling_update(supplement("2026-10-08", TECENTRIQ_RMC, TECENTRIQ_IU)))

    def test_original_approval_is_never_a_labeling_update(self):
        drug = supplement("2026-06-03", self.LABEL_ONLY_RMC, [])
        drug["submission_type"] = "ORIG"
        self.assertFalse(fda_approvals.is_labeling_update(drug))


def summarize(drugs, cache):
    # The committed summarizer takes an API key; the local-Ollama one does not.
    params = inspect.signature(fda_approvals.summarize_indications_batch).parameters
    extra = {"api_key": "test"} if "api_key" in params else {}
    return fda_approvals.summarize_indications_batch(drugs, summaries_cache=cache, **extra)


class TestSummarizeLabelingUpdate(unittest.TestCase):
    def labeling_drug(self, number="5"):
        return supplement(
            "2026-06-03", TestIsLabelingUpdate.LABEL_ONLY_RMC, [],
            application_number="NDA000001", submission_number=number,
            new_indication_text="pediatric labeling text pursuant to the Pediatric Research Equity Act (PREA)",
        )

    @patch("fda_approvals.urlopen", side_effect=AssertionError("model must not be called"))
    def test_labeling_update_skips_model_and_is_cached(self, _urlopen):
        drug, cache = self.labeling_drug(), {}
        summarize([drug], cache)
        self.assertEqual(drug["indication_summary"], "Labeling update")
        self.assertEqual(cache, {"NDA000001:SUPPL:5:2026-06-03": "Labeling update"})

    @patch("fda_approvals.urlopen", side_effect=AssertionError("model must not be called"))
    def test_cached_value_is_kept(self, _urlopen):
        drug = self.labeling_drug()
        cache = {"NDA000001:SUPPL:5:2026-06-03": "Pediatric atopic dermatitis"}
        summarize([drug], cache)
        self.assertEqual(drug["indication_summary"], "Pediatric atopic dermatitis")
        self.assertEqual(cache["NDA000001:SUPPL:5:2026-06-03"], "Pediatric atopic dermatitis")


if __name__ == "__main__":
    unittest.main()
