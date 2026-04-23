#!/usr/bin/env python3
"""Build the FDA drug approvals static site from JSON data."""

import json
import sys
import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape


DATA_PATH = "data/approvals.json"
TEMPLATE_DIR = "templates"
OUTPUT_DIR = "site"

REQUIRED_ASSETS = [
    "site/css/custom.css",
    "site/js/list.min.js",
    "site/js/main.js",
]


def format_date(value):
    if not value:
        return ""
    try:
        dt = datetime.strptime(value, "%Y-%m-%d")
        return dt.strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return value


def main():
    # Verify required assets exist
    for asset in REQUIRED_ASSETS:
        if not os.path.exists(asset):
            print(f"Error: Required asset missing: {asset}", file=sys.stderr)
            sys.exit(1)

    if not os.path.exists(DATA_PATH):
        print(f"Error: {DATA_PATH} not found. Run fda_approvals.py first.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(DATA_PATH) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error reading {DATA_PATH}: {e}", file=sys.stderr)
        sys.exit(1)

    drugs = data.get("drugs", [])

    required_fields = ["brand_name", "generic_name", "approval_date", "application_number", "type_badge", "slug"]
    for i, drug in enumerate(drugs):
        name = drug.get("brand_name") or drug.get("generic_name") or f"drug_{i}"
        for field in required_fields:
            if not drug.get(field):
                print(f"Error: Missing required field '{field}' in {name}", file=sys.stderr)
                sys.exit(1)

    # Compute last_updated from data metadata (AUTO-05)
    query_meta = data.get("query", {})
    date_to = query_meta.get("date_to")
    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d")
            last_updated = dt.strftime("%B %d, %Y")
        except (ValueError, TypeError):
            last_updated = datetime.now().strftime("%B %d, %Y")
    else:
        # Fallback: use file modification time
        mtime = os.path.getmtime(DATA_PATH)
        last_updated = datetime.fromtimestamp(mtime).strftime("%B %d, %Y")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["format_date"] = format_date

    template = env.get_template("index.html")
    html = template.render(
        drugs=drugs,
        last_updated=last_updated,
    )

    output_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(output_path, "w") as f:
        f.write(html)

    print(f"Built {output_path} with {len(drugs)} drug approvals (data through {date_to or 'unknown'})")


if __name__ == "__main__":
    main()