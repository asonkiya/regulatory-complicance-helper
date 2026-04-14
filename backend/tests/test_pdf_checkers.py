"""
Unit tests for the new PDF accessibility checkers and normalizer data structures.
Covers: MISSING_HEADING_STRUCTURE, MISSING_LINK_TEXT, MISSING_TABLE_HEADERS,
        MISSING_DOCUMENT_TITLE, and the NormalizedPage/NormalizedDocument round-trip.
"""
import pytest

from app.processing.normalizers import NormalizedDocument, NormalizedPage
from app.processing.checkers.pdf_content_checker import check_pdf_content
from app.processing.checkers.pdf_tag_checker import check_pdf_tags
from app.processing.checkers.structure_checker import check_structure


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_pdf_doc(pages=None, is_tagged_pdf=False, has_pdf_language=True,
                 has_document_title=True) -> NormalizedDocument:
    return NormalizedDocument(
        asset_id="test",
        source_type="PDF",
        pages=pages or [],
        is_tagged_pdf=is_tagged_pdf,
        has_pdf_language=has_pdf_language,
        has_document_title=has_document_title,
    )


def make_page(page_index=0, text_blocks=None, hyperlinks=None, tables=None,
              is_scanned=False) -> NormalizedPage:
    return NormalizedPage(
        page_index=page_index,
        text_blocks=text_blocks or [],
        hyperlinks=hyperlinks or [],
        tables=tables or [],
        is_scanned=is_scanned,
    )


# ── NormalizedPage serialization round-trip ────────────────────────────────────

class TestNormalizedPageRoundTrip:
    def test_new_fields_serialize(self):
        page = make_page(
            hyperlinks=[{"text": "here", "url": "https://example.com", "bbox": [0, 0, 50, 10], "page_index": 0}],
            tables=[{"bbox": [0, 0, 200, 100], "row_count": 3, "col_count": 2, "has_header_row": False}],
        )
        d = page.to_dict()
        assert "hyperlinks" in d
        assert "tables" in d
        restored = NormalizedPage.from_dict(d)
        assert restored.hyperlinks == page.hyperlinks
        assert restored.tables == page.tables

    def test_old_json_without_new_fields_deserializes_safely(self):
        """Old normalized JSON files (no hyperlinks/tables keys) must not crash."""
        old_dict = {
            "page_index": 0,
            "text_blocks": [{"text": "Hello", "bbox": [0, 0, 50, 10], "font_size": 12, "font_name": "Arial"}],
            "elements": [],
            "ocr_confidence": None,
            "is_scanned": False,
            # hyperlinks and tables keys intentionally absent
        }
        page = NormalizedPage.from_dict(old_dict)
        assert page.hyperlinks == []
        assert page.tables == []

    def test_has_document_title_round_trip(self):
        doc = make_pdf_doc(has_document_title=True)
        restored = NormalizedDocument.from_dict(doc.to_dict())
        assert restored.has_document_title is True

    def test_old_doc_json_without_has_document_title(self):
        old_dict = {
            "asset_id": "abc",
            "source_type": "PDF",
            "slides": [], "pages": [], "media": None, "metadata": {},
            "is_tagged_pdf": True, "has_pdf_language": True,
            # has_document_title absent
        }
        doc = NormalizedDocument.from_dict(old_dict)
        assert doc.has_document_title is None


# ── MISSING_HEADING_STRUCTURE ─────────────────────────────────────────────────

class TestMissingHeadingStructure:
    def _make_page_with_heading(self, heading_size=24.0, body_size=12.0) -> NormalizedPage:
        return make_page(text_blocks=[
            {"text": "Introduction to Neuroscience", "font_size": heading_size, "bbox": [0, 0, 300, 20]},
            {"text": "This course covers", "font_size": body_size, "bbox": [0, 25, 300, 35]},
            {"text": "the human brain and", "font_size": body_size, "bbox": [0, 40, 300, 50]},
        ])

    def test_heading_detected_in_untagged_pdf(self):
        doc = make_pdf_doc(pages=[self._make_page_with_heading()], is_tagged_pdf=False)
        issues = check_structure(doc)
        types = [i.issue_type for i in issues]
        assert "MISSING_HEADING_STRUCTURE" in types

    def test_no_issue_for_tagged_pdf(self):
        doc = make_pdf_doc(pages=[self._make_page_with_heading()], is_tagged_pdf=True)
        issues = check_structure(doc)
        types = [i.issue_type for i in issues]
        assert "MISSING_HEADING_STRUCTURE" not in types

    def test_no_issue_when_no_candidate_headings(self):
        page = make_page(text_blocks=[
            {"text": "all body text", "font_size": 12.0, "bbox": [0, 0, 100, 10]},
            {"text": "more body text", "font_size": 11.0, "bbox": [0, 15, 100, 25]},
        ])
        doc = make_pdf_doc(pages=[page], is_tagged_pdf=False)
        issues = check_structure(doc)
        assert not any(i.issue_type == "MISSING_HEADING_STRUCTURE" for i in issues)

    def test_no_issue_when_page_has_no_text(self):
        doc = make_pdf_doc(pages=[make_page()], is_tagged_pdf=False)
        issues = check_structure(doc)
        assert not any(i.issue_type == "MISSING_HEADING_STRUCTURE" for i in issues)

    def test_location_contains_candidate_headings(self):
        doc = make_pdf_doc(pages=[self._make_page_with_heading()], is_tagged_pdf=False)
        issues = check_structure(doc)
        heading_issues = [i for i in issues if i.issue_type == "MISSING_HEADING_STRUCTURE"]
        assert heading_issues
        loc = heading_issues[0].location_in_asset
        assert "page" in loc
        assert "candidate_headings" in loc
        assert "Introduction to Neuroscience" in loc["candidate_headings"]

    def test_candidate_headings_capped_at_five(self):
        # Seven headings at 24pt; 20 body lines at 10pt so body dominates the average
        # avg ≈ (7*24 + 20*10) / 27 = 13.6 → threshold 20.4 → 24pt clears it
        heading_blocks = [
            {"text": f"Chapter {i}", "font_size": 24.0, "bbox": [0, i * 30, 200, i * 30 + 20]}
            for i in range(7)
        ]
        body_blocks = [
            {"text": f"Body text line {i}.", "font_size": 10.0, "bbox": [0, 250 + i * 15, 300, 260 + i * 15]}
            for i in range(20)
        ]
        doc = make_pdf_doc(pages=[make_page(text_blocks=heading_blocks + body_blocks)], is_tagged_pdf=False)
        issues = check_structure(doc)
        heading_issues = [i for i in issues if i.issue_type == "MISSING_HEADING_STRUCTURE"]
        assert heading_issues, "Expected MISSING_HEADING_STRUCTURE when headings outnumber body avg"
        assert len(heading_issues[0].location_in_asset["candidate_headings"]) <= 5

    def test_very_long_text_not_treated_as_heading(self):
        """Text >= 150 chars should not be classified as a heading."""
        long_text = "A" * 150
        page = make_page(text_blocks=[
            {"text": long_text, "font_size": 24.0, "bbox": [0, 0, 400, 20]},
            {"text": "body", "font_size": 12.0, "bbox": [0, 25, 400, 35]},
        ])
        doc = make_pdf_doc(pages=[page], is_tagged_pdf=False)
        issues = check_structure(doc)
        assert not any(i.issue_type == "MISSING_HEADING_STRUCTURE" for i in issues)

    def test_pptx_doc_not_checked(self):
        """Structure checker should still work normally for PPTX docs (no heading check)."""
        from app.processing.normalizers import NormalizedSlide
        doc = NormalizedDocument(
            asset_id="test", source_type="PPTX",
            slides=[NormalizedSlide(slide_index=0, title="OK title", elements=[])],
        )
        issues = check_structure(doc)
        assert not any(i.issue_type == "MISSING_HEADING_STRUCTURE" for i in issues)


# ── MISSING_LINK_TEXT ──────────────────────────────────────────────────────────

class TestMissingLinkText:
    def _make_doc_with_link(self, text: str, url: str = "https://example.com") -> NormalizedDocument:
        page = make_page(hyperlinks=[{"text": text, "url": url, "bbox": [0, 0, 50, 10], "page_index": 0}])
        return make_pdf_doc(pages=[page])

    @pytest.mark.parametrize("bad_text", [
        "click here", "Click Here", "here", "HERE",
        "read more", "more", "link", "learn more",
        "this link", "this", "url", "more info", "details",
    ])
    def test_ambiguous_link_text_flagged(self, bad_text):
        doc = self._make_doc_with_link(bad_text)
        issues = check_pdf_content(doc)
        types = [i.issue_type for i in issues]
        assert "MISSING_LINK_TEXT" in types

    def test_raw_url_as_link_text_flagged(self):
        doc = self._make_doc_with_link("https://example.com/very-long-url")
        issues = check_pdf_content(doc)
        assert any(i.issue_type == "MISSING_LINK_TEXT" for i in issues)

    def test_empty_link_text_flagged(self):
        doc = self._make_doc_with_link("")
        issues = check_pdf_content(doc)
        assert any(i.issue_type == "MISSING_LINK_TEXT" for i in issues)

    def test_descriptive_link_text_not_flagged(self):
        doc = self._make_doc_with_link("Download the accessibility guidelines PDF")
        issues = check_pdf_content(doc)
        assert not any(i.issue_type == "MISSING_LINK_TEXT" for i in issues)

    def test_link_location_contains_url_and_text(self):
        doc = self._make_doc_with_link("click here", url="https://example.com/syllabus")
        issues = check_pdf_content(doc)
        link_issues = [i for i in issues if i.issue_type == "MISSING_LINK_TEXT"]
        assert link_issues
        loc = link_issues[0].location_in_asset
        assert loc["url"] == "https://example.com/syllabus"
        assert loc["link_text"] == "click here"
        assert "page" in loc

    def test_punctuation_stripped_before_deny_list_check(self):
        """'here.' and 'here,' should still be caught."""
        doc = self._make_doc_with_link("here.")
        issues = check_pdf_content(doc)
        assert any(i.issue_type == "MISSING_LINK_TEXT" for i in issues)

    def test_multiple_bad_links_each_flagged(self):
        page = make_page(hyperlinks=[
            {"text": "click here", "url": "https://a.com", "bbox": [0, 0, 50, 10], "page_index": 0},
            {"text": "read more", "url": "https://b.com", "bbox": [0, 20, 50, 30], "page_index": 0},
            {"text": "Download lecture notes PDF", "url": "https://c.com", "bbox": [0, 40, 200, 50], "page_index": 0},
        ])
        doc = make_pdf_doc(pages=[page])
        issues = check_pdf_content(doc)
        link_issues = [i for i in issues if i.issue_type == "MISSING_LINK_TEXT"]
        assert len(link_issues) == 2

    def test_no_links_no_issues(self):
        doc = make_pdf_doc(pages=[make_page()])
        issues = check_pdf_content(doc)
        assert not any(i.issue_type == "MISSING_LINK_TEXT" for i in issues)

    def test_non_pdf_doc_skipped(self):
        doc = NormalizedDocument(asset_id="test", source_type="PPTX")
        assert check_pdf_content(doc) == []


# ── MISSING_TABLE_HEADERS ─────────────────────────────────────────────────────

class TestMissingTableHeaders:
    def _make_doc_with_table(self, row_count: int, has_header_row: bool) -> NormalizedDocument:
        table = {
            "bbox": [0, 0, 300, 100],
            "row_count": row_count,
            "col_count": 3,
            "has_header_row": has_header_row,
        }
        page = make_page(tables=[table])
        return make_pdf_doc(pages=[page])

    def test_table_without_header_flagged(self):
        doc = self._make_doc_with_table(row_count=5, has_header_row=False)
        issues = check_pdf_content(doc)
        assert any(i.issue_type == "MISSING_TABLE_HEADERS" for i in issues)

    def test_table_with_header_not_flagged(self):
        doc = self._make_doc_with_table(row_count=5, has_header_row=True)
        issues = check_pdf_content(doc)
        assert not any(i.issue_type == "MISSING_TABLE_HEADERS" for i in issues)

    def test_single_row_table_not_flagged(self):
        """One-row tables can't meaningfully have a separate header."""
        doc = self._make_doc_with_table(row_count=1, has_header_row=False)
        issues = check_pdf_content(doc)
        assert not any(i.issue_type == "MISSING_TABLE_HEADERS" for i in issues)

    def test_severity_is_serious(self):
        doc = self._make_doc_with_table(row_count=3, has_header_row=False)
        issues = check_pdf_content(doc)
        table_issues = [i for i in issues if i.issue_type == "MISSING_TABLE_HEADERS"]
        assert table_issues[0].severity == "SERIOUS"

    def test_confidence_score_set(self):
        doc = self._make_doc_with_table(row_count=3, has_header_row=False)
        issues = check_pdf_content(doc)
        table_issues = [i for i in issues if i.issue_type == "MISSING_TABLE_HEADERS"]
        assert table_issues[0].confidence_score == pytest.approx(0.75)

    def test_location_contains_row_count(self):
        doc = self._make_doc_with_table(row_count=4, has_header_row=False)
        issues = check_pdf_content(doc)
        table_issues = [i for i in issues if i.issue_type == "MISSING_TABLE_HEADERS"]
        assert table_issues[0].location_in_asset["row_count"] == 4

    def test_no_tables_no_issues(self):
        doc = make_pdf_doc(pages=[make_page()])
        issues = check_pdf_content(doc)
        assert not any(i.issue_type == "MISSING_TABLE_HEADERS" for i in issues)


# ── MISSING_DOCUMENT_TITLE ────────────────────────────────────────────────────

class TestMissingDocumentTitle:
    def test_tagged_pdf_without_title_flagged(self):
        doc = make_pdf_doc(is_tagged_pdf=True, has_pdf_language=True, has_document_title=False)
        issues = check_pdf_tags(doc)
        assert any(i.issue_type == "MISSING_DOCUMENT_TITLE" for i in issues)

    def test_tagged_pdf_with_title_not_flagged(self):
        doc = make_pdf_doc(is_tagged_pdf=True, has_pdf_language=True, has_document_title=True)
        issues = check_pdf_tags(doc)
        assert not any(i.issue_type == "MISSING_DOCUMENT_TITLE" for i in issues)

    def test_untagged_pdf_without_title_not_flagged_separately(self):
        """UNTAGGED_PDF already covers this; don't double-report MISSING_DOCUMENT_TITLE."""
        doc = make_pdf_doc(is_tagged_pdf=False, has_document_title=False)
        issues = check_pdf_tags(doc)
        assert not any(i.issue_type == "MISSING_DOCUMENT_TITLE" for i in issues)
        assert any(i.issue_type == "UNTAGGED_PDF" for i in issues)

    def test_missing_document_title_is_auto_fixable(self):
        doc = make_pdf_doc(is_tagged_pdf=True, has_document_title=False)
        issues = check_pdf_tags(doc)
        title_issues = [i for i in issues if i.issue_type == "MISSING_DOCUMENT_TITLE"]
        assert title_issues[0].auto_fixable is True

    def test_missing_document_title_severity_moderate(self):
        doc = make_pdf_doc(is_tagged_pdf=True, has_document_title=False)
        issues = check_pdf_tags(doc)
        title_issues = [i for i in issues if i.issue_type == "MISSING_DOCUMENT_TITLE"]
        assert title_issues[0].severity == "MODERATE"

    def test_has_document_title_none_does_not_flag(self):
        """None means unknown (e.g., old normalized JSON); don't emit false positives."""
        doc = make_pdf_doc(is_tagged_pdf=True, has_document_title=None)
        issues = check_pdf_tags(doc)
        assert not any(i.issue_type == "MISSING_DOCUMENT_TITLE" for i in issues)


# ── Combined check_pdf_content ────────────────────────────────────────────────

class TestCheckPdfContentCombined:
    def test_both_link_and_table_issues_returned(self):
        page = make_page(
            hyperlinks=[{"text": "click here", "url": "https://x.com", "bbox": [0, 0, 50, 10], "page_index": 0}],
            tables=[{"bbox": [0, 20, 200, 80], "row_count": 3, "col_count": 2, "has_header_row": False}],
        )
        doc = make_pdf_doc(pages=[page])
        issues = check_pdf_content(doc)
        types = {i.issue_type for i in issues}
        assert "MISSING_LINK_TEXT" in types
        assert "MISSING_TABLE_HEADERS" in types
