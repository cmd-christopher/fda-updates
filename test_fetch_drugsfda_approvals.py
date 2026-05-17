import unittest
from unittest.mock import patch
from datetime import datetime
import fda_approvals

class TestFetchDrugsfdaApprovals(unittest.TestCase):
    @patch('fda_approvals._fetch_paginated_results')
    def test_fetch_drugsfda_approvals_filtering(self, mock_fetch):
        # 1. Valid record
        valid_record = {
            "application_number": "NDA001",
            "openfda": {
                "brand_name": ["ValidBrand"],
                "generic_name": ["ValidGeneric"]
            },
            "submissions": [
                {
                    "submission_type": "ORIG",
                    "submission_status": "AP",
                    "submission_status_date": "20230115"
                }
            ],
            "products": [
                {
                    "marketing_status": "Prescription"
                }
            ]
        }

        # 2. Missing ORIG/AP submission
        missing_orig_ap = {
            "application_number": "NDA002",
            "openfda": {
                "brand_name": ["Brand2"]
            },
            "submissions": [
                {
                    "submission_type": "SUPPL",
                    "submission_status": "AP",
                    "submission_status_date": "20230115"
                }
            ],
            "products": [{"marketing_status": "Prescription"}]
        }

        # 3. Approval date out of bounds (before 2023-01-01)
        out_of_bounds_date = {
            "application_number": "NDA003",
            "openfda": {"brand_name": ["Brand3"]},
            "submissions": [
                {
                    "submission_type": "ORIG",
                    "submission_status": "AP",
                    "submission_status_date": "20221231"
                }
            ],
            "products": [{"marketing_status": "Prescription"}]
        }

        # 4. Approval date out of bounds (after 2023-01-31)
        out_of_bounds_date2 = {
            "application_number": "NDA004",
            "openfda": {"brand_name": ["Brand4"]},
            "submissions": [
                {
                    "submission_type": "ORIG",
                    "submission_status": "AP",
                    "submission_status_date": "20230201"
                }
            ],
            "products": [{"marketing_status": "Prescription"}]
        }

        # 5. Missing brand/generic names
        missing_names = {
            "application_number": "NDA005",
            "openfda": {},
            "submissions": [
                {
                    "submission_type": "ORIG",
                    "submission_status": "AP",
                    "submission_status_date": "20230115"
                }
            ],
            "products": [{"marketing_status": "Prescription"}]
        }

        # 6. Missing prescription marketing status
        missing_prescription = {
            "application_number": "NDA006",
            "openfda": {"brand_name": ["Brand6"]},
            "submissions": [
                {
                    "submission_type": "ORIG",
                    "submission_status": "AP",
                    "submission_status_date": "20230115"
                }
            ],
            "products": [
                {"marketing_status": "Over-the-counter"}
            ]
        }

        # 7. Valid record with marketing status "1"
        valid_record_2 = {
            "application_number": "NDA007",
            "openfda": {
                "brand_name": ["ValidBrand2"]
            },
            "submissions": [
                {
                    "submission_type": "ORIG",
                    "submission_status": "AP",
                    "submission_status_date": "20230115"
                }
            ],
            "products": [
                {
                    "marketing_status": "1"
                }
            ]
        }

        mock_fetch.return_value = [
            valid_record,
            missing_orig_ap,
            out_of_bounds_date,
            out_of_bounds_date2,
            missing_names,
            missing_prescription,
            valid_record_2
        ]

        date_from = datetime(2023, 1, 1)
        date_to = datetime(2023, 1, 31)

        result = fda_approvals.fetch_drugsfda_approvals(date_from, date_to)

        self.assertEqual(len(result), 2)

        self.assertEqual(result[0]["application_number"], "NDA001")
        self.assertEqual(result[0]["brand_name"], "ValidBrand")

        self.assertEqual(result[1]["application_number"], "NDA007")

if __name__ == '__main__':
    unittest.main()
