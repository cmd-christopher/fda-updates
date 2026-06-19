#!/usr/bin/env python3
"""Coverage tests for build.py — targeting lines not exercised by test_build.py.

These tests use the same mocking strategy as test_build.py: bleach/jinja2/markupsafe
are stubbed so the module imports without the real third-party stack for the
formatting/sanitizing logic, and os/filesystem calls are patched for the
file-writing functions.
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

# Mock third-party dependencies before importing build (same pattern as test_build.py)
import re


def dummy_clean(text, tags=None, attributes=None, strip=False):
    text = str(text)
    if strip:
        text = re.sub(r'<form>', '', text)
        text = re.sub(r'</form>', '', text)
        text = re.sub(r'<input[^>]*>', '', text)
        text = text.replace('Test</p>Submit', 'Test</p>\nSubmit')
        text = re.sub(r'\s+onclick="[^"]*"', '', text)
        text = re.sub(r'\s+style="[^"]*"', '', text)
    return text


mock_bleach = MagicMock()
mock_bleach.clean = dummy_clean
sys.modules['bleach'] = mock_bleach

sys.modules['jinja2'] = MagicMock()

mock_markupsafe = MagicMock()
mock_markupsafe.Markup = lambda x: str(x)
sys.modules['markupsafe'] = mock_markupsafe

import build


class TestFormatPiTextEmpty(unittest.TestCase):
    """Cover the empty/None early-return branch (line 213)."""

    def test_empty_string(self):
        self.assertEqual(build.format_pi_text(""), "")

    def test_none(self):
        self.assertEqual(build.format_pi_text(None), "")


class TestFormatPiTextTablesAndLists(unittest.TestCase):
    """Cover the table/list protection save branches (lines 220-221, 226-227)."""

    def test_table_protected_and_reinserted(self):
        text = "<table><tr><td>cell</td></tr></table> after table"
        result = build.format_pi_text(text)
        # Table placeholder is reinserted in the body
        self.assertIn("<table>", result)

    def test_list_protected_and_reinserted(self):
        text = "<ul><li>item</li></ul> after list"
        result = build.format_pi_text(text)
        self.assertIn("<ul>", result)


class TestFormatPiTextLeadIn(unittest.TestCase):
    """Cover the indication lead-in detection (lines 263-282)."""

    def test_lead_in_becomes_list_with_subsections(self):
        text = (
            "DRUG is indicated for the treatment of: "
            "psoriasis ( 1.1 ) arthritis ( 1.2 ) "
            "1.1 Psoriasis is a chronic condition. 1.2 Arthritis is inflammatory."
        )
        result = build.format_pi_text(text)
        self.assertIn("indication-lead", result)
        self.assertIn("pi-list", result)

    def test_lead_in_no_subsections_returns_just_list(self):
        # Remainder has no sub-section headings -> returns just the indication list
        text = (
            "DRUG is indicated for the treatment of: "
            "psoriasis ( 1.1 ) arthritis ( 1.2 )"
        )
        result = build.format_pi_text(text)
        self.assertIn("indication-lead", result)
        self.assertIn("pi-list", result)

    def test_lead_in_match_but_no_paren_refs(self):
        # "indicated for the treatment of: ..." but group(2) has no "( N.N )" refs
        text = "DRUG is indicated for the treatment of a single condition. More text follows."
        result = build.format_pi_text(text)
        # Should not produce an indication list
        self.assertNotIn("indication-lead", result)


class TestFormatPiTextSubsectionSplit(unittest.TestCase):
    """Cover sub-section heading splitting (lines 290-305, 308-312)."""

    def test_subsection_headings_split(self):
        text = (
            "2 DOSAGE AND ADMINISTRATION "
            "COSENTYX is a drug. "
            "2.1 Dosage in Adults The dose is 300 mg. "
            "2.2 Dosage in Pediatrics The dose is 150 mg."
        )
        result = build.format_pi_text(text)
        self.assertIn("pi-subsection", result)
        self.assertIn("Dosage in Adults", result)
        self.assertIn("Dosage in Pediatrics", result)

    def test_no_sections_returns_body(self):
        # No sub-section headings found -> falls through to body
        text = "Just some plain body text with no headings here."
        result = build.format_pi_text(text)
        self.assertIn("<p>", result)


class TestFormatPiTextBullets(unittest.TestCase):
    """Cover bullet list detection (lines 353-369)."""

    def test_bullet_list_detected(self):
        text = "Some intro text.\n- item one\n- item two\n- item three"
        result = build.format_pi_text(text)
        self.assertIn("pi-list", result)
        self.assertIn("<li>item one</li>", result)

    def test_bullet_list_then_text_closes_list(self):
        text = "Intro.\n- item one\n- item two\nFollow up text here."
        result = build.format_pi_text(text)
        self.assertIn("pi-list", result)
        # List should be closed before the follow-up text
        self.assertIn("</ul>", result)


class TestFormatPiTextHtmlStartBranch(unittest.TestCase):
    """Cover the _HTML_TAG_START_RE branch (372->375)."""

    def test_existing_html_not_wrapped_in_p(self):
        # Body starting with an HTML tag should not be wrapped in <p> by _split_long_paragraphs
        text = "<div>already html</div>"
        result = build.format_pi_text(text)
        self.assertIn("<div>", result)


class TestParseHeadingTitleLine162(unittest.TestCase):
    """Cover line 162: break when title_parts non-empty and next is lowercase non-connector."""

    def test_breaks_on_lowercase_after_title_parts(self):
        # "Adverse" -> title, "Reactions" -> title candidate, "reported" -> lowercase non-connector
        # At i=1 (Reactions), next_w="reported" triggers break at 162 before Reactions is added
        self.assertEqual(build._parse_heading_title(["Adverse", "Reactions", "reported"]), "Adverse")

    def test_no_break_when_next_is_title_word(self):
        # When next word is a title word (not lowercase), parsing continues
        self.assertEqual(build._parse_heading_title(["Adverse", "Reactions"]), "Adverse Reactions")


class TestSplitLongParagraphsBranches(unittest.TestCase):
    """Cover remaining _split_long_paragraphs branches (76->78, 103->106, 116->119)."""

    def test_short_text_colon_single_part(self):
        # Colon present but only one part -> falls through to single <p>
        text = "NoSplitHere"
        # No colon, short
        self.assertEqual(build._split_long_paragraphs(text, max_chars=100), "<p>NoSplitHere</p>")

    def test_short_with_colon_multiple_parts(self):
        # Split after colon when followed by uppercase: "Heading: Body"
        text = "Warning: This is important."
        result = build._split_long_paragraphs(text, max_chars=100)
        self.assertIn("<p>Warning:</p>", result)
        self.assertIn("<p>This is important.</p>", result)

    def test_long_sentence_temp_remaining_appended(self):
        # Long sentence that, after force-splitting, leaves a remainder that
        # becomes the new current (line 103->106 and 116->119)
        text = "a" * 50 + " " + "b" * 50 + " " + "short sentence after."
        result = build._split_long_paragraphs(text, max_chars=30)
        # Should produce multiple <p> chunks
        self.assertIn("<p>", result)
        chunks = result.split("\n")
        self.assertGreater(len(chunks), 1)


class TestSetupJinjaEnv(unittest.TestCase):
    """Cover setup_jinja_env (lines 494-501)."""

    def test_setup_jinja_env_registers_filters(self):
        # jinja2 is mocked, so Environment returns a MagicMock.
        # We verify that env.filters __setitem__ is called for each filter.
        env = build.setup_jinja_env()
        # The mock should have had filters assigned
        # Since env.filters is a MagicMock, check __setitem__ calls
        self.assertTrue(env.filters.__setitem__.called)
        # Verify the three filters were registered
        setitem_calls = env.filters.__setitem__.call_args_list
        filter_names = [call.args[0] for call in setitem_calls]
        self.assertIn("format_date", filter_names)
        self.assertIn("sanitize_html", filter_names)
        self.assertIn("format_pi_text", filter_names)


class TestGenerateIndexPage(unittest.TestCase):
    """Cover generate_index_page (lines 505-518)."""

    @patch('build.os.makedirs')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_generate_index_page(self, mock_open, mock_makedirs):
        mock_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "<html>index</html>"
        mock_env.get_template.return_value = mock_template

        drugs = [{"slug": "drug-a"}]
        build.generate_index_page(mock_env, drugs, "Jan 01, 2026", "2026-01-01")

        mock_env.get_template.assert_called_once_with("index.html")
        mock_template.render.assert_called_once()
        mock_makedirs.assert_called_once_with(build.OUTPUT_DIR, exist_ok=True)
        mock_open.assert_called_once()

    @patch('build.os.makedirs')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_generate_index_page_none_date_to(self, mock_open, mock_makedirs):
        mock_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "<html></html>"
        mock_env.get_template.return_value = mock_template

        build.generate_index_page(mock_env, [], "Jan 01, 2026", None)
        # date_to is None -> 'unknown' appears in printed message; render called
        mock_template.render.assert_called_once()


class TestGenerateDetailPages(unittest.TestCase):
    """Cover generate_detail_pages (lines 522-541)."""

    @patch('build.os.makedirs')
    @patch('build.os.listdir', return_value=["old.html", "keep.txt"])
    @patch('build.os.remove')
    @patch('build.os.path.isdir', return_value=True)
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_generate_detail_pages_cleans_old_and_writes_new(
        self, mock_open, mock_isdir, mock_remove, mock_listdir, mock_makedirs
    ):
        mock_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "<html>detail</html>"
        mock_env.get_template.return_value = mock_template

        drugs = [
            {"slug": "drug-a", "brand_name": "A"},
            {"slug": "drug-b", "brand_name": "B"},
        ]
        build.generate_detail_pages(mock_env, drugs, "Jan 01, 2026")

        # Should have removed old .html files
        mock_remove.assert_any_call(os.path.join(build.OUTPUT_DIR, "drugs", "old.html"))
        # Should render a template per drug
        self.assertEqual(mock_template.render.call_count, 2)
        # Should open a file per drug for writing
        self.assertEqual(mock_open.call_count, 2)

    @patch('build.os.makedirs')
    @patch('build.os.path.isdir', return_value=False)
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_generate_detail_pages_no_existing_dir(self, mock_open, mock_isdir, mock_makedirs):
        mock_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "<html>detail</html>"
        mock_env.get_template.return_value = mock_template

        build.generate_detail_pages(mock_env, [{"slug": "x"}], "Jan 01, 2026")
        mock_makedirs.assert_called_once_with(os.path.join(build.OUTPUT_DIR, "drugs"), exist_ok=True)


class TestBuildMain(unittest.TestCase):
    """Cover build.main() (lines 545-561)."""

    @patch('build.generate_detail_pages')
    @patch('build.generate_index_page')
    @patch('build.setup_jinja_env')
    @patch('build.compute_last_updated', return_value="Jan 01, 2026")
    @patch('build.resolve_slug_collisions')
    @patch('build.validate_drug_data')
    @patch('build.load_data')
    @patch('build.verify_assets')
    def test_main_full_flow(
        self, mock_verify, mock_load, mock_validate, mock_resolve, mock_compute,
        mock_setup, mock_gen_index, mock_gen_detail
    ):
        mock_load.return_value = {"drugs": [{"slug": "x"}], "query": {"date_to": "2026-01-01"}}
        mock_env = MagicMock()
        mock_setup.return_value = mock_env

        with self.assertLogs("build", level="INFO"):
            build.main()

        mock_verify.assert_called_once()
        mock_load.assert_called_once()
        mock_validate.assert_called_once()
        mock_resolve.assert_called_once()
        mock_compute.assert_called_once()
        mock_setup.assert_called_once()
        mock_gen_index.assert_called_once()
        mock_gen_detail.assert_called_once()


class TestComputeLastUpdatedDateToPresentButInvalidType(unittest.TestCase):
    """Cover compute_last_updated where date_to present but strptime raises TypeError."""

    @patch('build.datetime')
    def test_date_to_list_type(self, mock_datetime):
        mock_datetime.strptime = datetime.strptime
        fixed_now = datetime(2024, 1, 5)
        mock_datetime.now.return_value = fixed_now
        data = {"query": {"date_to": ["not-a-date"]}}
        result = build.compute_last_updated(data)
        self.assertEqual(result, "January 05, 2024")


if __name__ == "__main__":
    unittest.main()