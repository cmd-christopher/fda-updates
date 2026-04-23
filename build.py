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


def format_date(value):
    if not value:
        return ""
    try:
        dt = datetime.strptime(value, "%Y-%m-%d")
        return dt.strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return value


def main():
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

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["format_date"] = format_date

    template = env.get_template("index.html")
    html = template.render(
        drugs=drugs,
        last_updated=datetime.now().strftime("%B %d, %Y"),
    )

    output_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(output_path, "w") as f:
        f.write(html)

    print(f"Built {output_path} with {len(drugs)} drug approvals")


if __name__ == "__main__":
    main()