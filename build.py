#!/usr/bin/env python3
"""Build the FDA drug approvals static site from JSON data."""

import json
import re
import sys
import os
from datetime import datetime
import bleach
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

    # Strip <script>, <style>, <iframe> tags and their content first
    # This prevents bleach from leaving raw JS/CSS text behind on the page
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<iframe[^>]*>.*?</iframe>", "", text, flags=re.DOTALL | re.IGNORECASE)

    allowed_tags = [
        "table", "p", "br", "ul", "ol", "li", "b", "i", "strong",
        "em", "h1", "h2", "h3", "h4", "h5", "h6", "sub", "sup",
        "div", "span", "a", "thead", "tbody", "tr", "td", "th"
    ]

    allowed_attributes = {
        "*": ["class", "id"],
        "a": ["href", "title"]
    }

    # Bleach will safely strip disallowed tags like script, style, and iframe
    # It will also strip disallowed attributes like on* and style
    cleaned_text = bleach.clean(
        text,
        tags=allowed_tags,
        attributes=allowed_attributes,
        strip=True
    )

    return Markup(cleaned_text)


def _split_long_paragraphs(text, max_chars=800):
    """Split text into multiple <p> blocks if it exceeds max_chars.
    Also splits at colons if they appear to separate logical blocks.
    """
    if len(text) <= max_chars:
        # Still try to split at colons if they look like headings
        if ":" in text:
            parts = re.split(r"(?<=[a-z])\.\s+(?=[A-Z])|(?<=:)\s+(?=[A-Z])", text)
            if len(parts) > 1:
                return "\n".join(f"<p>{p.strip()}</p>" for p in parts if p.strip())
        return f"<p>{text}</p>"

    # Split at sentence boundaries or colons
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])|(?<=:)\s+(?=[A-Z])", text)
    chunks = []
    current = []
    current_len = 0

    for sentence in sentences:
        s_len = len(sentence)
        if s_len > max_chars:
            # Force split long sentence
            if current:
                chunks.append("<p>" + " ".join(current) + "</p>")
                current = []
                current_len = 0
            
            temp_sentence = sentence
            while len(temp_sentence) > max_chars:
                split_at = temp_sentence.rfind(" ", 0, max_chars)
                if split_at == -1:
                    split_at = max_chars
                chunks.append(f"<p>{temp_sentence[:split_at]}</p>")
                temp_sentence = temp_sentence[split_at:].lstrip()
            
            if temp_sentence:
                current.append(temp_sentence)
                current_len = len(temp_sentence)
            continue

        if current and current_len + s_len > max_chars:
            chunks.append("<p>" + " ".join(current) + "</p>")
            current.clear()
            current_len = 0

        current.append(sentence)
        current_len += s_len + 1

    if current:
        chunks.append("<p>" + " ".join(current) + "</p>")

    return "\n".join(chunks)


_SENTENCE_STARTERS = frozenset({
    "The", "This", "These", "It", "Its",
    "Because", "When", "If", "Due", "Based",
    "Patients", "Patient", "Adults", "Adult", "Children",
    "Assess", "Monitor", "Evaluate", "Determine", "Measure",
    "Coadministration", "Concomitant", "Discontinue",
})

_CONNECTORS = frozenset({"of", "and", "in", "for", "with"})


def _parse_heading_title(words, max_plain=6, max_chars=55):
    """Parse sub-section heading title from word list after the section number."""
    title_parts = []
    i = 0

    while i < len(words):
        clean = words[i].strip(".,;:")
        is_title_word = bool(
            re.match(r"^[A-Z][a-z]+$", clean)
            or re.match(r"^[A-Z][A-Z0-9]+[a-z]*$", clean)
            or re.match(r"^[A-Z][a-z]+-[A-Z][a-z]+$", clean)
        )

        if is_title_word:
            if i + 1 < len(words):
                next_w = words[i + 1].strip(".,;:")
                if re.match(r"^[a-z]+$", next_w) and next_w not in _CONNECTORS:
                    if title_parts:
                        break

            test_plain = sum(
                1 for w in title_parts + [clean]
                if w[0].isupper() and w.lower() not in _CONNECTORS
            )
            test_title = " ".join(title_parts + [clean])
            if test_plain > max_plain or len(test_title) > max_chars:
                break

            title_parts.append(clean)

            if i + 1 < len(words):
                next_clean = words[i + 1].strip(".,;:")
                is_next_connector = (
                    next_clean.lower() in _CONNECTORS
                    and not bool(re.match(r"^[A-Z][a-z]+$", next_clean))
                )
                if is_next_connector:
                    title_parts.append(next_clean)
                    i += 2
                    continue

            if i + 1 < len(words):
                nw = words[i + 1].strip(".,;:")
                if re.match(r"^[A-Z]{2,}$", nw):
                    break
                if re.match(r"^[a-z]", nw):
                    break
                if nw in _SENTENCE_STARTERS:
                    break
            i += 1
        else:
            break

    while title_parts and title_parts[-1].lower() in _CONNECTORS:
        title_parts.pop()

    return " ".join(title_parts) if title_parts else None


def format_pi_text(text):
    """Format FDA prescribing information text for readability.

    Three-stage pipeline:
    1. Pre-process: strip section header, detect indication lead-in lists,
       remove cross-refs that duplicate sub-section structure
    2. Split: separate text at sub-section headings (N.N Title)
    3. Post-process: style cross-refs, detect bullet lists, split long paragraphs
    """
    if not text:
        return Markup("")

    text = str(text)

    # --- Protect existing HTML tables and lists ---
    tables = []
    def _save_table(m):
        tables.append(m.group(0))
        return f"%%TABLE{len(tables) - 1}%%"
    text = re.sub(r"<table[^>]*>.*?</table>", _save_table, text, flags=re.DOTALL | re.IGNORECASE)

    lists_html = []
    def _save_list(m):
        lists_html.append(m.group(0))
        return f"%%LIST{len(lists_html) - 1}%%"
    text = re.sub(r"<(?:ul|ol)[^>]*>.*?</(?:ul|ol)>", _save_list, text, flags=re.DOTALL | re.IGNORECASE)

    # --- Stage 1: Pre-process ---

    text = text.strip()

    # Strip the top-level section header like "2 DOSAGE AND ADMINISTRATION"
    # Use known FDA section titles to avoid greedily consuming the first word of content
    # (which is often a drug name in ALL CAPS like "COSENTYX" or a Title Case word like "Prior")
    _SECTION_HEADERS = (
        "INDICATIONS AND USAGE|INDICATIONS & USAGE|"
        "DOSAGE AND ADMINISTRATION|DOSAGE & ADMINISTRATION|"
        "DOSAGE FORMS AND STRENGTHS|DOSAGE FORM AND STRENGTHS|"
        "CONTRAINDICATIONS|WARNINGS AND PRECAUTIONS|"
        "ADVERSE REACTIONS|DRUG INTERACTIONS|"
        "USE IN SPECIFIC POPULATIONS|OVERDOSAGE|"
        "DESCRIPTION|CLINICAL PHARMACOLOGY|CLINICAL STUDIES|"
        "NONCLINICAL TOXICOLOGY|HOW SUPPLIED|"
        "MECHANISM OF ACTION|PATIENT COUNSELING INFORMATION|"
        "ABUSE AND DEPENDENCE|BOXED WARNING"
    )
    text = re.sub(rf"^\d+\s+(?:{_SECTION_HEADERS})\s*", "", text)

    # Detect indication lead-in pattern and convert to bullet list
    # Pattern: "DRUG is indicated/recommended for [the treatment of]: item1. (1.1) item2. (1.2) ..."
    lead_in_re = re.compile(
        r"^([\s\S]{0,300}?(?:indicated|recommended)\s*(?:for|as)?\s*(?:the\s+)?"
        r"(?:treatment|management|therapy|use|adjunct|adjuvant|first-line|monotherapy|combination)?[\s\S]{0,100}?[:.])\s*"
        r"([\s\S]*)",
        re.DOTALL | re.IGNORECASE,
    )
    indication_list_html = None
    lead_sentence = None
    m = lead_in_re.match(text)
    if m and "( " in m.group(2) and re.search(r"\(\s*\d+\.\d+\s*\)", m.group(2)):
        lead_sentence = m.group(1).strip().rstrip(":")
        remainder = m.group(2)
        # Split at cross-reference boundaries: text before ( N.N ) becomes list items
        items = re.split(r"\s*\(\s*\d+(?:\.\d+)?(?:\s*,\s*\d+(?:\.\d+)?)*\s*\)\s*", remainder)
        items = [item.strip() for item in items if item.strip()]
        if len(items) >= 2:
            li_parts = [f"<li>{item}</li>" for item in items]
            indication_list_html = '<p class="indication-lead">' + lead_sentence + ':</p>\n<ul class="pi-list">' + "".join(li_parts) + "</ul>"
            # Remove the lead-in portion from text so it's not double-rendered
            # Find where the sub-section headings start
            subsec_match = re.search(r"(?:^|\s)\d+\.\d+\s+[A-Z][a-z]", remainder)
            if subsec_match:
                text = remainder[subsec_match.start():].lstrip()
            else:
                text = remainder
                # Check if remainder still has sub-section headings
                if not re.search(r"\d+\.\d+\s+[A-Z][a-z]", text):
                    # No sub-sections left — just the indication list
                    indication_list_html = _style_xrefs_in_body(indication_list_html)
                    return Markup(indication_list_html)

    # --- Stage 2: Split at sub-section headings ---

    sections = []
    last_end = 0
    # IMPROVED REGEX: Allow space, start of string, or closing parenthesis
    for m in re.finditer(r"(?:^|[\s\)])(\d+(?:\.\d+)+)\s+([A-Z])", text):
        num = m.group(1)
        # Find where the number actually starts in the match (skip the leading space/paren if any)
        num_start = m.start() + m.group(0).find(num)
        
        title_start = m.end() - len(m.group(2))
        after_num = text[title_start:]
        title_words = after_num.split()
        title = _parse_heading_title(title_words)

        if title and len(title) > 2:
            body_before = text[last_end:num_start].strip()
            if body_before:
                sections.append(("body", body_before))
            sections.append(("heading", num, title))
            title_end_in_after = after_num.lower().find(title.lower()) + len(title)
            last_end = title_start + title_end_in_after

    remaining = text[last_end:].strip()
    if remaining:
        sections.append(("body", remaining))

    if not sections:
        sections.append(("body", text.strip()))

    # --- Stage 3: Post-process and convert to HTML ---

    result_parts = []
    if indication_list_html:
        result_parts.append(indication_list_html)

    for section in sections:
        if section[0] == "heading":
            _, num, title = section
            result_parts.append(f'<h4 class="pi-subsection"><span class="sub-num">{num}</span> {title}</h4>')
        else:
            _, body = section
            body = body.strip()
            if not body:
                continue

            # Reinsert protected tables/lists
            body = re.sub(
                r"%%TABLE(\d+)%%",
                lambda m: tables[int(m.group(1))] if int(m.group(1)) < len(tables) else m.group(0),
                body
            )
            body = re.sub(
                r"%%LIST(\d+)%%",
                lambda m: lists_html[int(m.group(1))] if int(m.group(1)) < len(lists_html) else m.group(0),
                body
            )

            # Style cross-references
            body = _style_xrefs_in_body(body)

            # Bold "Title Case: " or "ALL CAPS: " patterns (sub-sub-headings)
            # Allows for common connectors like 'of', 'in', 'and'
            body = re.sub(r"(^|<p>|:\s+)([A-Z][A-Z0-9a-z]*(?:\s+(?:and|or|of|in|for|with|to|at|vs|[A-Z][A-Z0-9a-z]*)){0,6}):\s+", r'\1<strong>\2:</strong> ', body)

            # Detect simple bullet lists (• or dash-prefixed lines)
            lines = body.split("\n")
            has_bullets = sum(1 for l in lines if re.match(r"^\s*[•\-\*]\s+", l))
            if has_bullets >= 2:
                formatted_lines = []
                in_list = False
                for l in lines:
                    if re.match(r"^\s*[•\-\*]\s+", l):
                        if not in_list:
                            formatted_lines.append('<ul class="pi-list">')
                            in_list = True
                        item = re.sub(r"^\s*[•\-\*]\s+", "", l)
                        formatted_lines.append(f"<li>{item}</li>")
                    else:
                        if in_list:
                            formatted_lines.append("</ul>")
                            in_list = False
                        formatted_lines.append(l)
                if in_list:
                    formatted_lines.append("</ul>")
                body = "\n".join(formatted_lines)

            # Wrap in <p> or split long text
            if not re.match(r"^\s*<(?:h[1-6]|div|ul|ol|table|p|blockquote)", body, re.IGNORECASE):
                body = _split_long_paragraphs(body)

            result_parts.append(body)

    result = "\n".join(result_parts)
    return Markup(result)


def _style_xrefs_in_body(text):
    """Style cross-references in body text."""
    text = re.sub(
        r"(\[see\s+[^]]*?)\(\s*(\d+(?:\.\d+)?(?:\s*,\s*\d+(?:\.\d+)?)*)\s*\)([^]]*?\])",
        r'\1<span class="xref">\2</span>\3',
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\(\s*(\d+(?:\.\d+)?(?:\s*,\s*\d+(?:\.\d+)?)*)\s*\)",
        r'<span class="xref">(\1)</span>',
        text,
    )
    return text


DATA_PATH = "data/approvals.json"
NON_DIGIT_RE = re.compile(r"\D")
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


def verify_assets():
    for asset in REQUIRED_ASSETS:
        if not os.path.exists(asset):
            print(f"Error: Required asset missing: {asset}", file=sys.stderr)
            sys.exit(1)


def load_data():
    if not os.path.exists(DATA_PATH):
        print(f"Error: {DATA_PATH} not found. Run fda_approvals.py first.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(DATA_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error reading {DATA_PATH}: {e}", file=sys.stderr)
        sys.exit(1)


def validate_drug_data(drugs):
    required_fields = ["brand_name", "generic_name", "approval_date", "application_number", "type_badge", "slug"]
    for i, drug in enumerate(drugs):
        name = drug.get("brand_name") or drug.get("generic_name") or f"drug_{i}"
        for field in required_fields:
            if not drug.get(field):
                print(f"Error: Missing required field '{field}' in {name}", file=sys.stderr)
                sys.exit(1)


def resolve_slug_collisions(drugs):
    slug_counts = {}
    for drug in drugs:
        base_slug = drug["slug"]
        slug = base_slug
        if slug in slug_counts:
            digits = NON_DIGIT_RE.sub("", drug.get("application_number", ""))
            slug = f"{base_slug}-{digits}" if digits else f"{base_slug}-{slug_counts[base_slug]}"
        if slug in slug_counts:
            date_suffix = drug.get("approval_date", "").replace("-", "")
            slug = f"{slug}-{date_suffix}" if date_suffix else f"{slug}-{slug_counts[slug]}"
        drug["slug"] = slug
        slug_counts[slug] = slug_counts.get(slug, 0) + 1


def compute_last_updated(data):
    query_meta = data.get("query", {})
    date_to = query_meta.get("date_to")
    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d")
            return dt.strftime("%B %d, %Y")
        except (ValueError, TypeError):
            return datetime.now().strftime("%B %d, %Y")
    else:
        # Fallback: use file modification time
        mtime = os.path.getmtime(DATA_PATH)
        return datetime.fromtimestamp(mtime).strftime("%B %d, %Y")


def setup_jinja_env():
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["format_date"] = format_date
    env.filters["sanitize_html"] = sanitize_html
    env.filters["format_pi_text"] = format_pi_text
    return env


def generate_index_page(env, drugs, last_updated, date_to):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    template = env.get_template("index.html")
    html = template.render(
        drugs=drugs,
        last_updated=last_updated,
        root_path="",
    )

    output_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(output_path, "w") as f:
        f.write(html)

    print(f"Built {output_path} with {len(drugs)} drug approvals (data through {date_to or 'unknown'})")


def generate_detail_pages(env, drugs, last_updated):
    drugs_dir = os.path.join(OUTPUT_DIR, "drugs")
    if os.path.isdir(drugs_dir):
        for f in os.listdir(drugs_dir):
            if f.endswith(".html"):
                os.remove(os.path.join(drugs_dir, f))
    os.makedirs(drugs_dir, exist_ok=True)

    detail_template = env.get_template("drug_detail.html")
    for drug in drugs:
        detail_html = detail_template.render(
            drug=drug,
            last_updated=last_updated,
            root_path="../",
        )
        detail_path = os.path.join(drugs_dir, f"{drug['slug']}.html")
        with open(detail_path, "w") as f:
            f.write(detail_html)

    print(f"Built {len(drugs)} drug detail pages in {drugs_dir}")


def main():
    verify_assets()
    data = load_data()
    drugs = data.get("drugs", [])

    validate_drug_data(drugs)
    resolve_slug_collisions(drugs)

    last_updated = compute_last_updated(data)
    env = setup_jinja_env()

    query_meta = data.get("query", {})
    date_to = query_meta.get("date_to")

    generate_index_page(env, drugs, last_updated, date_to)
    generate_detail_pages(env, drugs, last_updated)


if __name__ == "__main__":
    main()