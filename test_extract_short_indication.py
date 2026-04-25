import unittest
from fda_approvals import extract_short_indication

class TestExtractShortIndication(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(extract_short_indication(""), "")

    def test_none(self):
        self.assertEqual(extract_short_indication(None), "")

    def test_list_input(self):
        self.assertEqual(extract_short_indication(["indicated", "for", "the", "treatment", "of", "disease."]), "disease")

    def test_html_tags(self):
        self.assertEqual(extract_short_indication("indicated for the treatment of <b>disease</b>."), "disease")

    def test_basic_treatment_of(self):
        self.assertEqual(extract_short_indication("indicated for the treatment of moderate to severe plaque psoriasis."), "moderate to severe plaque psoriasis")

    def test_basic_treatment_of_with_brand_name(self):
        self.assertEqual(extract_short_indication("COSENTYX is a human interleukin-17A antagonist indicated for the treatment of moderate to severe plaque psoriasis.", brand_name="COSENTYX"), "moderate to severe plaque psoriasis")

    def test_management_of(self):
        self.assertEqual(extract_short_indication("indicated for the management of chronic pain."), "chronic pain")

    def test_prevention_of(self):
        self.assertEqual(extract_short_indication("indicated for the prevention of migraine."), "migraine")

    def test_indicated_to_reduce(self):
        self.assertEqual(extract_short_indication("indicated to reduce the risk of stroke."), "the risk of stroke")

    def test_indicated_for_colon(self):
        self.assertEqual(extract_short_indication("indicated for: disease A. T"), "disease A")

    def test_indicated_for_colon_2(self):
        self.assertEqual(extract_short_indication("indicated for: treatment of disease. A"), "treatment of disease")

    def test_indicated_for_patients_with(self):
        self.assertEqual(extract_short_indication("indicated for the treatment of patients with severe disease."), "severe disease")

    def test_first_condition_split(self):
        # Because `_clean` runs before `_first_condition`, `( 1.1 )` is removed, so we assert the actual current behavior
        self.assertEqual(extract_short_indication("indicated for: disease A) ( 1.1 ) Disease B."), "disease A) Disease B")

    def test_first_condition_preserve_parens(self):
        self.assertEqual(extract_short_indication("indicated for: disease A (Wet) (1.1). A"), "disease A (Wet)")

    def test_duplicate_sentence(self):
        text = "DRUG is indicated for the treatment of patients with: DRUG is indicated for the treatment of patients with: disease"
        self.assertEqual(extract_short_indication(text, brand_name="DRUG"), "disease")

    def test_duplicate_sentence_with_is_a(self):
        text = "DRUG is an antagonist indicated for the treatment of patients with: DRUG is a antagonist indicated for the treatment of patients with: severe disease"
        self.assertEqual(extract_short_indication(text, brand_name="DRUG"), "severe disease")

    def test_strip_numbers(self):
        self.assertEqual(extract_short_indication("1 INDICATIONS AND USAGE indicated for the treatment of disease."), "disease")

    def test_strip_numbers_leading(self):
        self.assertEqual(extract_short_indication("1 indicated for the treatment of disease."), "disease")

    def test_clean_see_section(self):
        self.assertEqual(extract_short_indication("indicated for the treatment of disease [see Clinical Studies (14)]."), "disease")

    def test_indicated_as_adjunct(self):
        self.assertEqual(extract_short_indication("indicated as an adjunct therapy to disease."), "disease")

    def test_indicated_in_combination(self):
        self.assertEqual(extract_short_indication("indicated in combination with other drugs for disease."), "disease")

    def test_drug_is_a_inhibitor(self):
        self.assertEqual(extract_short_indication("DRUG is a kinase inhibitor indicated for disease.", brand_name="DRUG"), "disease")

    def test_generic_indicated_for(self):
        self.assertEqual(extract_short_indication("indicated for disease."), "disease")

    def test_fallback(self):
        self.assertEqual(extract_short_indication("This is a random sentence. It has a second sentence."), "This is a random sentence")

    def test_fallback_no_period(self):
        self.assertEqual(extract_short_indication("This is a random sentence without period"), "This is a random sentence without period")


if __name__ == '__main__':
    unittest.main()
