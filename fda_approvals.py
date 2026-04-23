#!/usr/bin/env python3
"""Retrieve FDA prescription drug approvals from a date range, then fetch full label information for each drug.

Usage:
    python fda_approvals.py --from 2026-01-01 --to 2026-04-22
    python fda_approvals.py --from 2026-01-01 --to 2026-04-22 --type nme
    python fda_approvals.py --from 2026-01-01 --to 2026-04-22 --output approvals.json
"""

import argparse
import json
import sys
import time
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from urllib.parse import quote

API_BASE = "https://api.fda.gov/drug/"
REQUEST_DELAY = 0.5


def fetch_json(url):
    req = Request(url, headers={"User-Agent": "fda-approvals-script/1.0"})
    with urlopen(req) as resp:
        return json.loads(resp.read().decode())


def fetch_drugsfda_approvals(date_from, date_to, submission_type=None, limit=100):
    date_from_str = date_from.strftime("%Y%m%d")
    date_to_str = date_to.strftime("%Y%m%d")
    date_from_int = int(date_from_str)
    date_to_int = int(date_to_str)

    search_parts = [
        'submissions.submission_type:ORIG',
        'submissions.submission_status:AP',
    ]
    if submission_type:
        search_parts.append(
            f'submissions.submission_class_code_description:"{submission_type}"'
        )

    search = "+AND+".join(search_parts)
    url = f"{API_BASE}drugsfda.json?search={quote(search, safe='+:[]')}&sort=submissions.submission_status_date:desc&limit={limit}"

    all_results = []
    skip = 0
    while True:
        page_url = f"{url}&skip={skip}" if skip > 0 else url
        data = fetch_json(page_url)
        results = data.get("results", [])
        all_results.extend(results)
        if len(results) < limit or len(all_results) >= data.get("meta", {}).get("results", {}).get("total", 0):
            break
        skip += limit

    drugs = []
    for entry in all_results:
        orig_sub = None
        for s in entry.get("submissions", []):
            if s.get("submission_type") == "ORIG" and s.get("submission_status") == "AP":
                orig_sub = s
                break

        if not orig_sub:
            continue

        approval_date_raw = orig_sub.get("submission_status_date", "")
        if len(approval_date_raw) == 8:
            approval_int = int(approval_date_raw)
            if approval_int < date_from_int or approval_int > date_to_int:
                continue

        openfda = entry.get("openfda", {})
        brand_names = openfda.get("brand_name", [])
        generic_names = openfda.get("generic_name", [])
        if not brand_names and not generic_names:
            continue

        products = entry.get("products", [])
        is_prescription = any(
            p.get("marketing_status") == "Prescription" or p.get("marketing_status") == "1"
            for p in products
        )
        if not is_prescription:
            continue

        approval_date = orig_sub.get("submission_status_date", "")
        approval_date_fmt = f"{approval_date[:4]}-{approval_date[4:6]}-{approval_date[6:8]}" if len(approval_date) == 8 else approval_date

        drug = {
            "brand_name": brand_names[0] if brand_names else None,
            "generic_name": generic_names[0] if generic_names else None,
            "all_brand_names": brand_names,
            "all_generic_names": generic_names,
            "approval_date": approval_date_fmt,
            "application_number": entry.get("application_number", ""),
            "submission_class": orig_sub.get("submission_class_code_description", ""),
            "review_priority": orig_sub.get("review_priority", ""),
            "sponsor_name": entry.get("sponsor_name", ""),
            "manufacturer_name": openfda.get("manufacturer_name", []),
            "route": openfda.get("route", []),
            "pharm_class_epc": openfda.get("pharm_class_epc", []),
            "pharm_class_moa": openfda.get("pharm_class_moa", []),
            "products": [
                {
                    "brand_name": p.get("brand_name", ""),
                    "active_ingredients": p.get("active_ingredients", []),
                    "dosage_form": p.get("dosage_form", ""),
                    "route": p.get("route", ""),
                    "marketing_status": p.get("marketing_status", ""),
                }
                for p in products
                if p.get("marketing_status") in ("Prescription", "1")
            ],
            "rxcui": openfda.get("rxcui", []),
            "unii": openfda.get("unii", []),
        }
        drugs.append(drug)

    return drugs


def fetch_label(drug):
    brand_name = drug.get("brand_name") or drug.get("all_brand_names", [""])[0]
    app_num = drug.get("application_number", "")

    search = f'search=openfda.application_number:"{app_num}"&limit=1'

    try:
        url = f"{API_BASE}label.json?{search}"
        time.sleep(REQUEST_DELAY)
        data = fetch_json(url)
        results = data.get("results", [])
        if not results:
            return None
        label = results[0]

        fields = [
            "indications_and_usage",
            "boxed_warning",
            "dosage_and_administration",
            "dosage_forms_and_strengths",
            "contraindications",
            "warnings_and_cautions",
            "adverse_reactions",
            "drug_interactions",
            "use_in_specific_populations",
            "recent_major_changes",
            "mechanism_of_action",
            "clinical_pharmacology",
            "clinical_studies",
            "patient_counseling_information",
            "nonclinical_toxicology",
            "overdosage",
            "description",
        ]

        label_data = {}
        for field in fields:
            val = label.get(field)
            if val:
                label_data[field] = val

        label_data["openfda"] = label.get("openfda", {})
        return label_data

    except HTTPError as e:
        if e.code == 404:
            return None
        print(f"  Warning: HTTP {e.code} fetching label for {brand_name}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve FDA prescription drug approvals and full label information."
    )
    parser.add_argument(
        "--from", dest="date_from", required=True,
        help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--to", dest="date_to", required=True,
        help="End date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--type", dest="submission_type", default=None,
        choices=["nme", "all"],
        help="Filter: 'nme' for Type 1 New Molecular Entities only, 'all' for all original approvals (default: all)"
    )
    parser.add_argument(
        "--limit", type=int, default=100,
        help="Max number of drugsfda results to fetch (default: 100)"
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Output JSON file path (default: stdout)"
    )
    parser.add_argument(
        "--skip-labels", action="store_true",
        help="Skip label fetching (only return drugsfda data)"
    )

    args = parser.parse_args()

    date_from = datetime.strptime(args.date_from, "%Y-%m-%d")
    date_to = datetime.strptime(args.date_to, "%Y-%m-%d")

    type_filter = 'Type 1 - New Molecular Entity' if args.submission_type == 'nme' else None

    print(f"Fetching drugsfda approvals from {args.date_from} to {args.date_to}...", file=sys.stderr)
    drugs = fetch_drugsfda_approvals(date_from, date_to, submission_type=type_filter, limit=args.limit)
    print(f"Found {len(drugs)} prescription drug approvals.", file=sys.stderr)

    if not args.skip_labels:
        print("Fetching labels...", file=sys.stderr)
        for i, drug in enumerate(drugs, 1):
            name = drug.get("brand_name") or drug.get("generic_name") or "Unknown"
            print(f"  [{i}/{len(drugs)}] {name}...", file=sys.stderr)
            label = fetch_label(drug)
            drug["label"] = label

    output = {
        "query": {
            "date_from": args.date_from,
            "date_to": args.date_to,
            "submission_type_filter": args.submission_type or "all",
        },
        "count": len(drugs),
        "drugs": drugs,
    }

    json_str = json.dumps(output, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(json_str)
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(json_str)


if __name__ == "__main__":
    main()