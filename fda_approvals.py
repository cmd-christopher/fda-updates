#!/usr/bin/env python3
"""Retrieve FDA prescription drug approvals from a date range, then fetch full label information for each drug.

Usage:
    python fda_approvals.py --from 2026-01-01 --to 2026-04-22
    python fda_approvals.py --from 2026-01-01 --to 2026-04-22 --type nme
    python fda_approvals.py --from 2026-01-01 --to 2026-04-22 --type suppl
    python fda_approvals.py --from 2026-01-01 --to 2026-04-22 --output approvals.json
"""

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from urllib.parse import quote

API_BASE = "https://api.fda.gov/drug/"
REQUEST_DELAY = 0.5
LABEL_CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", ".label_cache.json")
INDICATION_SUMMARIES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", ".indication_summaries.json")
LLM_API_URL = "https://ollama.com/v1/chat/completions"
LLM_MODEL = "cogito-2.1:671b"
LLM_BATCH_SIZE = 10

EFFICACY_SUPPL_CODES = {"EFFICACY"}


def fetch_json(url):
    req = Request(url, headers={"User-Agent": "fda-approvals-script/1.0"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def slugify(name):
    if not name:
        return ""
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = name.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[-\s]+", "-", name)
    return name.strip("-")


def extract_short_indication(text, brand_name=""):
    """Extract a concise indication from FDA label text.

    Turns verbose FDA indications like:
      "COSENTYX is a human interleukin-17A antagonist indicated for
       the treatment of moderate to severe plaque psoriasis..."
    Into:
      "moderate to severe plaque psoriasis"
    """
    if not text:
        return ""
    if isinstance(text, list):
        text = " ".join(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"^\d+(\.\d+)*\s+INDICATIONS?\s+AND\s+USAGE\s*", "", text, flags=re.IGNORECASE)
    text = text.strip()
    if not text:
        return ""
    if text[0].isdigit() and text[1:2] == " ":
        text = re.sub(r"^\d+\s+", "", text)

    def _clean(s):
        s = re.sub(r"\s*\(\s*\d+(\.\d+)?\s*\)", "", s).strip()
        s = re.sub(r"\s*\[\s*see\s+.*?\]", "", s, flags=re.IGNORECASE).strip()
        return s.rstrip(";:,.").strip()

    def _first_condition(s):
        """Take the first condition from a colon-separated or semicolon list.

        Splits on section references like (1.2) or ( 1.2 ) followed by a new condition,
        but preserves parenthetical qualifiers like (Wet) or (nAMD) that are part of
        the condition name.
        """
        # Split on section-reference parens: "( 1.X )" or "(1.X)" followed by a capital letter
        # that starts a new condition name. These look like "nAMD) ( 1.1 ) Diabetic"
        # But DON'T split on "(Wet) Age" — parenthetical qualifiers within condition names.
        parts = re.split(r"\)\s*\(\s*\d+(?:\.\d+)?\s*\)\s+(?=[A-Z])", s, maxsplit=1)
        result = parts[0] if parts else s
        result = re.sub(r"\s*\(\s*\d+(\.\d+)?\s*\)$", "", result).strip()
        return result.rstrip(";:,.").strip()

    clean_name = re.sub(r"\s+(TM|®|℠)", "", brand_name, flags=re.IGNORECASE) if brand_name else ""

    # FDA duplicate-sentence: "DRUG is ... indicated for ... : DRUG is ... indicated for ... : Cond1 (1.1) Cond2 (1.2)"
    if clean_name:
        dup = re.search(
            r"indicated for\s+.+?:\s*(?:" + re.escape(clean_name) + r"\s+is\s+a?\s*|is\s+)?(?:.+?\s+)?indicated for\s+(?:the\s+)?(?:treatment|management|prevention|use)\s+of\s+(?:patients\s+with\s*:\s*)(.+)",
            text, re.IGNORECASE,
        )
        if dup:
            return _first_condition(_clean(dup.group(1)))[:100]

    # "indicated for the treatment/management/etc of: CONDITIONS" (colon list)
    m = re.search(
        r"indicated for\s+(?:the\s+)?(?:treatment|management|prevention|reduction|use|prophylaxis)\s+of\s+(?:patients\s+(?:with|who)\s+)?:?\s*(.+?)(?:\.\s+(?:\(\s*\d)|\.\s+[A-Z]|\.$)",
        text, re.IGNORECASE | re.DOTALL,
    )
    if m:
        return _first_condition(_clean(m.group(1)))[:100]

    # "indicated for the treatment/etc of CONDITION"
    m = re.search(
        r"indicated for\s+(?:the\s+)?(?:treatment|management|prevention|reduction|use|prophylaxis)\s+of\s+(.+?)(?:\.(?:\s|$))",
        text, re.IGNORECASE,
    )
    if m:
        return _clean(m.group(1))[:100]

    # "DRUG is indicated for: CONDITION" (colon, no treatment/management keyword)
    m = re.search(r"indicated for:\s*(.+?)(?:\.\s+[A-Z]|\.$)", text, re.IGNORECASE | re.DOTALL)
    if m:
        return _first_condition(_clean(m.group(1)))[:100]

    # "indicated to reduce/increase/improve/etc CONDITION"
    m = re.search(
        r"indicated to\s+(?:reduce|increase|improve|treat|manage|prevent|lower|raise|decrease|control|maintain|provide|support)\s+(.+?)(?:\.(?:\s|$))",
        text, re.IGNORECASE,
    )
    if m:
        return _clean(m.group(1))[:100]

    # "indicated in/for/as [adjunct/combination/etc] [with] CONDITION"
    m = re.search(
        r"indicated\s+(?:as\s+(?:an?\s+)?(?:adjunct|add-on|first-line|second-line|monotherapy|combination|alternative|supplement|replacement|initial|maintenance)\s*(?:therapy|treatment|regimen|agent|option)?\s*(?:to|for|in|with)\s+|in\s+(?:combination\s+with\s+.+?\s+for\s+|adults?\s+(?:and\s+pediatric\s+patients?\s+)?(?:aged?\s+\d+\s+(?:years?\s+)?(?:and\s+older(?:\s+patients?\s+)?)?\s+)?with\s+|patients?\s+(?:aged?\s+\S+\s+)?with\s+|pediatric\s+patients\s+\S+\s+with\s+))(.+?)(?:\.(?:\s|$))",
        text, re.IGNORECASE,
    )
    if m:
        return _clean(m.group(1))[:100]

    # "DRUG [is a/an ... antagonist/inhibitor] indicated for/in/to CONDITION"
    if clean_name:
        m = re.search(
            re.escape(clean_name) + r"\s+(?:\([^)]*\)\s+)?(?:injection|tablet|capsule|cream|solution|for\s+injection)?\s*(?:is\s+(?:a\s+|an\s+)?\S+(?:\s+and\s+\S+)?\s+(?:antagonist|inhibitor|agonist|blocker|stimulant|modulator|therapy|treatment|antibody|receptor|product|medicine|drug|combination)\s+)?indicated\s+(?:for|in|to|as)\s+(.+?)(?:\.(?:\s|$))",
            text, re.IGNORECASE,
        )
        if m:
            return _clean(m.group(1))[:100]

    # Generic: "indicated for/in/to/as CONDITION"
    m = re.search(r"indicated\s+(?:for|in|to|as)\s+(.+?)(?:\.(?:\s|$))", text, re.IGNORECASE)
    if m:
        return _clean(m.group(1))[:100]

    # Fallback: first sentence
    m = re.search(r"(.+?)\.(?:\s|$)", text)
    if m:
        return m.group(1).strip()[:100]
    return text[:80].strip()


def load_indication_summaries(path=INDICATION_SUMMARIES_PATH):
    """Load previously LLM-summarized indications from cache."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_indication_summaries(summaries, path=INDICATION_SUMMARIES_PATH):
    """Save LLM-summarized indications to cache."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(summaries, f, indent=2, sort_keys=True)


def summarize_indications_batch(drugs, api_key, summaries_cache, batch_size=LLM_BATCH_SIZE):
    """Use LLM to produce concise 1-4 word condition names from verbose FDA indications.

    Batches drugs to minimize API calls. Uses cached summaries for previously processed drugs.
    """
    to_process = []
    for drug in drugs:
        app_num = drug.get("application_number", "")
        if app_num and app_num in summaries_cache:
            drug["indication_summary"] = summaries_cache[app_num]
        else:
            label = drug.get("label") or {}
            ind_text = ""
            if label and label.get("indications_and_usage"):
                raw = label["indications_and_usage"]
                ind_text = raw[0] if isinstance(raw, list) else raw
            if not ind_text:
                ind_text = drug.get("submission_class", "") or drug.get("submission_type", "")
            if ind_text:
                to_process.append((app_num, drug.get("brand_name", "") or drug.get("generic_name", ""), ind_text))

    if not to_process:
        return

    print(f"Summarizing {len(to_process)} indications via LLM (batches of {batch_size})...", file=sys.stderr)

    for batch_start in range(0, len(to_process), batch_size):
        batch = to_process[batch_start:batch_start + batch_size]
        lines = []
        for app_num, brand, text in batch:
            short_text = text[:300] if len(text) > 300 else text
            lines.append(f"{app_num}|{brand}|{short_text}")

        prompt_lines = [
            "For each drug below, extract ONLY the primary condition/disease name. 1-4 words max, no explanation.",
            "Format: APP_NUM|condition_name",
            "",
        ]
        for app_num, brand, text in batch:
            prompt_lines.append(f"{app_num}|{text[:300]}")

        prompt = "\n".join(prompt_lines)

        data = json.dumps({
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
        }).encode()

        req = Request(
            LLM_API_URL,
            data=data,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )

        try:
            with urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                content = result["choices"][0]["message"]["content"].strip()

            for line in content.strip().split("\n"):
                line = line.strip()
                if "|" in line:
                    parts = line.split("|", 1)
                    app_num = parts[0].strip()
                    condition = parts[1].strip().strip('"').strip("'")
                    if app_num and condition:
                        summaries_cache[app_num] = condition
                        for drug in drugs:
                            if drug.get("application_number") == app_num:
                                drug["indication_summary"] = condition

        except Exception as e:
            print(f"  Warning: LLM summarization batch failed: {e}", file=sys.stderr)
            for app_num, brand, text in batch:
                summaries_cache[app_num] = brand
                for drug in drugs:
                    if drug.get("application_number") == app_num:
                        drug["indication_summary"] = drug.get("brand_name", "") or drug.get("generic_name", "")

        time.sleep(0.5)


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
    search_parts.append(f"submissions.submission_status_date:[{date_from_str}+TO+{date_to_str}]")

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

        brand_name = brand_names[0] if brand_names else None
        generic_name = generic_names[0] if generic_names else None

        drug = {
            "brand_name": brand_name,
            "generic_name": generic_name,
            "all_brand_names": brand_names,
            "all_generic_names": generic_names,
            "approval_date": approval_date_fmt,
            "application_number": entry.get("application_number", ""),
            "submission_class": orig_sub.get("submission_class_code_description", ""),
            "submission_type": "ORIG",
            "type_badge": "New Drug",
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
        drug["slug"] = slugify(drug["brand_name"] or drug["generic_name"] or "")
        drugs.append(drug)

    return drugs


def fetch_suppl_approvals(date_from, date_to, limit=100):
    date_from_str = date_from.strftime("%Y%m%d")
    date_to_str = date_to.strftime("%Y%m%d")
    date_from_int = int(date_from_str)
    date_to_int = int(date_to_str)

    date_filter = f"+AND+submissions.submission_status_date:[{date_from_str}+TO+{date_to_str}]"
    search = f'submissions.submission_type:SUPPL+AND+submissions.submission_status:AP+AND+submissions.submission_class_code:EFFICACY{date_filter}'
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
    seen_keys = set()

    for entry in all_results:
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

        for s in entry.get("submissions", []):
            if s.get("submission_type") != "SUPPL":
                continue
            if s.get("submission_status") != "AP":
                continue

            code = s.get("submission_class_code", "")
            if code not in EFFICACY_SUPPL_CODES:
                continue

            date_raw = s.get("submission_status_date", "")
            if len(date_raw) == 8:
                date_int = int(date_raw)
                if date_int < date_from_int or date_int > date_to_int:
                    continue
            else:
                continue

            app_num = entry.get("application_number", "")
            approval_date_fmt = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:8]}"
            dedup_key = (app_num, approval_date_fmt, s.get("submission_number", ""))
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            brand_name = brand_names[0] if brand_names else None
            generic_name = generic_names[0] if generic_names else None

            drug = {
                "brand_name": brand_name,
                "generic_name": generic_name,
                "all_brand_names": brand_names,
                "all_generic_names": generic_names,
                "approval_date": approval_date_fmt,
                "application_number": app_num,
                "submission_class": s.get("submission_class_code_description", ""),
                "submission_type": "SUPPL",
                "type_badge": "New Indication",
                "review_priority": s.get("review_priority", ""),
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
            drug["slug"] = slugify(drug["brand_name"] or drug["generic_name"] or "")
            drugs.append(drug)

    return drugs


def fetch_label(drug):
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
        label_data["set_id"] = label.get("id", "")
        return label_data

    except HTTPError as e:
        if e.code == 404:
            return None
        name = drug.get("brand_name") or drug.get("generic_name") or "Unknown"
        print(f"  Warning: HTTP {e.code} fetching label for {name}", file=sys.stderr)
        return None


def load_previous_approvals(path="data/approvals.json"):
    """Load previous run's approvals.json to reuse label data for cached drugs."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
        prev = {}
        for drug in data.get("drugs", []):
            app_num = drug.get("application_number", "")
            if app_num and drug.get("label"):
                prev[app_num] = drug
        return prev
    except (json.JSONDecodeError, OSError):
        return {}


def save_label_cache(drugs, cache_path):
    """Save app_num → set_id mapping for future incremental runs."""
    cache = {}
    for drug in drugs:
        app_num = drug.get("application_number", "")
        label = drug.get("label")
        if app_num and label and label.get("set_id"):
            cache[app_num] = label["set_id"]
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(cache, f, indent=2)


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
        "--type", dest="submission_type", default="all",
        choices=["nme", "all", "suppl"],
        help="Filter: 'nme' for Type 1 NME only, 'suppl' for efficacy supplements only, 'all' for both (default: all)"
    )
    parser.add_argument(
        "--limit", type=int, default=100,
        help="Max number of drugsfda results per query (default: 100)"
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Output JSON file path (default: stdout)"
    )
    parser.add_argument(
        "--skip-labels", action="store_true",
        help="Skip label fetching (only return drugsfda data)"
    )
    parser.add_argument(
        "--cache", action="store_true",
        help="Use cached label data from previous run to skip re-fetching unchanged labels"
    )
    parser.add_argument(
        "--summarize", action="store_true",
        help="Use LLM to generate concise 1-4 word condition summaries for the indication column"
    )
    parser.add_argument(
        "--llm-api-key", default=None,
        help="API key for the LLM service (or set LLM_API_KEY env var)"
    )

    args = parser.parse_args()

    llm_key = args.llm_api_key or os.environ.get("LLM_API_KEY", "")

    date_from = datetime.strptime(args.date_from, "%Y-%m-%d")
    date_to = datetime.strptime(args.date_to, "%Y-%m-%d")

    drugs = []

    if args.submission_type == "nme":
        print(f"Fetching NME approvals from {args.date_from} to {args.date_to}...", file=sys.stderr)
        drugs = fetch_drugsfda_approvals(date_from, date_to, submission_type="Type 1 - New Molecular Entity", limit=args.limit)
        print(f"Found {len(drugs)} NME prescription drug approvals.", file=sys.stderr)
    elif args.submission_type == "suppl":
        print(f"Fetching efficacy SUPPL approvals from {args.date_from} to {args.date_to}...", file=sys.stderr)
        drugs = fetch_suppl_approvals(date_from, date_to, limit=args.limit)
        print(f"Found {len(drugs)} efficacy supplement approvals.", file=sys.stderr)
    else:
        print(f"Fetching ORIG + efficacy SUPPL approvals from {args.date_from} to {args.date_to}...", file=sys.stderr)
        orig_types = [
            "Type 1 - New Molecular Entity",
            "Type 2 - New Active Ingredient",
            "Type 4 - New Combination",
        ]
        orig_drugs = []
        for st in orig_types:
            orig_drugs.extend(fetch_drugsfda_approvals(date_from, date_to, submission_type=st, limit=args.limit))
        suppl_drugs = fetch_suppl_approvals(date_from, date_to, limit=args.limit)
        print(f"Found {len(orig_drugs)} ORIG (NME+Type2+Type4) and {len(suppl_drugs)} SUPPL approvals.", file=sys.stderr)
        drugs = orig_drugs + suppl_drugs
        drugs.sort(key=lambda d: d.get("approval_date", ""), reverse=True)

        seen = set()
        deduped = []
        for d in drugs:
            key = (d["application_number"], d["approval_date"], d["type_badge"])
            if key not in seen:
                seen.add(key)
                deduped.append(d)
        drugs = deduped
        print(f"After deduplication: {len(drugs)} unique approval events.", file=sys.stderr)

    if not args.skip_labels:
        # Load previous label data when --cache is provided
        previous_data = load_previous_approvals() if args.cache else {}
        if args.cache:
            cached_count = sum(1 for d in drugs if d.get("application_number") in previous_data and previous_data[d["application_number"]].get("label"))
            print(f"Cache: {cached_count} previously fetched labels available.", file=sys.stderr)

        print("Fetching labels...", file=sys.stderr)
        for i, drug in enumerate(drugs, 1):
            name = drug.get("brand_name") or drug.get("generic_name") or "Unknown"
            app_num = drug.get("application_number", "")

            # Check if we can reuse cached label data
            if args.cache and app_num in previous_data and previous_data[app_num].get("label"):
                drug["label"] = previous_data[app_num]["label"]
                drug["indication_preview"] = extract_short_indication(
                    drug["label"].get("indications_and_usage", [""])[0] if isinstance(drug["label"].get("indications_and_usage"), list) else drug["label"].get("indications_and_usage", ""),
                    brand_name=drug.get("brand_name") or drug.get("generic_name", ""),
                )
                print(f"  [{i}/{len(drugs)}] {name} (cached)", file=sys.stderr)
            else:
                print(f"  [{i}/{len(drugs)}] {name}...", file=sys.stderr)
                label = fetch_label(drug)
                drug["label"] = label
                if label:
                    drug["indication_preview"] = extract_short_indication(
                        label.get("indications_and_usage", [""])[0] if isinstance(label.get("indications_and_usage"), list) else label.get("indications_and_usage", ""),
                        brand_name=drug.get("brand_name") or drug.get("generic_name", ""),
                    )
                else:
                    drug["indication_preview"] = drug.get("submission_class", "") or drug.get("submission_type", "")

        # Save label cache after processing
        if args.cache:
            save_label_cache(drugs, LABEL_CACHE_PATH)
            print(f"Label cache written to {LABEL_CACHE_PATH}", file=sys.stderr)
    else:
        for drug in drugs:
            drug["label"] = None
            drug["indication_preview"] = drug.get("submission_class", "") or drug.get("submission_type", "")

    # LLM-based indication summarization
    if args.summarize:
        if not llm_key:
            print("Warning: --summarize requires --llm-api-key or LLM_API_KEY env var. Skipping.", file=sys.stderr)
        else:
            summaries_cache = load_indication_summaries()
            summarize_indications_batch(drugs, llm_key, summaries_cache)
            save_indication_summaries(summaries_cache)
            summarized = sum(1 for d in drugs if d.get("indication_summary"))
            print(f"Summarized {summarized}/{len(drugs)} indications via LLM", file=sys.stderr)

    output = {
        "query": {
            "date_from": args.date_from,
            "date_to": args.date_to,
            "submission_type_filter": args.submission_type,
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