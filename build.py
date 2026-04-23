#!/usr/bin/env python3
"""Build the FDA drug approvals static site from JSON data."""

import json
import re
import sys
import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup


def sanitize_html(text):
    """Strip dangerous HTML content, preserve safe structural tags.

    Removes: <script>, <style>, <iframe> tags and their content.
    Removes: event attributes (onclick, onerror, onload, onmouseover, etc.).
    Removes: style attributes.
    Preserves: safe structural tags (table, p, br, ul, ol, li, b, i, strong,
               em, h1-h6, sub, sup, div, span, a, thead, tbody, tr, td, th).

    Returns a Markup object marked safe for Jinja2 rendering.
    """
    if not text:
        return Markup("")

    # Strip <script>, <style>, <iframe> tags and their content
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<iframe[^>]*>.*?</iframe>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Strip event attributes (on*="...")
    text = re.sub(r'\s+on\w+\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)', "", text, flags=re.IGNORECASE)

    # Strip style attributes
    text = re.sub(r'\s+style\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)', "", text, flags=re.IGNORECASE)

    return Markup(text)


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

    # Resolve slug collisions — append digits from application_number
    slug_counts = {}
    for drug in drugs:
        slug = drug["slug"]
        if slug in slug_counts:
            # Extract numeric digits from application_number (e.g., "NDA123456" → "123456")
            digits = re.sub(r"\D", "", drug.get("application_number", ""))
            drug["slug"] = f"{slug}-{digits}" if digits else f"{slug}-{slug_counts[slug]}"
        slug_counts[drug["slug"]] = slug_counts.get(drug["slug"], 0) + 1

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
    env.filters["sanitize_html"] = sanitize_html

    template = env.get_template("index.html")
    html = template.render(
        drugs=drugs,
        last_updated=last_updated,
    )

    output_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(output_path, "w") as f:
        f.write(html)

    print(f"Built {output_path} with {len(drugs)} drug approvals (data through {date_to or 'unknown'})")

    # Generate detail pages for each drug
    drugs_dir = os.path.join(OUTPUT_DIR, "drugs")
    os.makedirs(drugs_dir, exist_ok=True)

    detail_template = env.get_template("drug_detail.html")
    for drug in drugs:
        detail_html = detail_template.render(
            drug=drug,
            last_updated=last_updated,
        )
        detail_path = os.path.join(drugs_dir, f"{drug['slug']}.html")
        with open(detail_path, "w") as f:
            f.write(detail_html)

    print(f"Built {len(drugs)} drug detail pages in {drugs_dir}")


if __name__ == "__main__":
    main()