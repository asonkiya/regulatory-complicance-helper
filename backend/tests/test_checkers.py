"""
Unit tests for accessibility checkers.
"""
import pytest
from app.processing.normalizers import (
    NormalizedDocument,
    NormalizedElement,
    NormalizedPage,
    NormalizedSlide,
)
from app.processing.checkers.alt_text_checker import check_alt_text
from app.processing.checkers.caption_checker import check_captions
from app.processing.checkers.contrast_checker import _contrast_ratio
from app.processing.checkers.pdf_tag_checker import check_pdf_tags
from app.processing.checkers.structure_checker import check_structure


def make_pptx_doc(slides=None) -> NormalizedDocument:
    return NormalizedDocument(
        asset_id="test-asset",
        source_type="PPTX",
        slides=slides or [],
    )


def make_pdf_doc(**kwargs) -> NormalizedDocument:
    return NormalizedDocument(asset_id="test-asset", source_type="PDF", **kwargs)


# ── Alt Text Checker ────────────────────────────────────────────────────────

class TestAltTextChecker:
    def test_missing_alt_text_flagged(self):
        slide = NormalizedSlide(
            slide_index=0,
            title="Slide 1",
            elements=[NormalizedElement(element_id="s0_img0", element_type="IMAGE", alt_text=None)],
        )
        doc = make_pptx_doc(slides=[slide])
        issues = check_alt_text(doc)
        assert len(issues) == 1
        assert issues[0].issue_type == "MISSING_ALT_TEXT"
        assert issues[0].severity == "CRITICAL"
        assert issues[0].auto_fixable is True

    def test_good_alt_text_not_flagged(self):
        slide = NormalizedSlide(
            slide_index=0,
            title="Slide 1",
            elements=[
                NormalizedElement(
                    element_id="s0_img0",
                    element_type="IMAGE",
                    alt_text="A bar chart showing sales growth from 2020 to 2024",
                )
            ],
        )
        doc = make_pptx_doc(slides=[slide])
        issues = check_alt_text(doc)
        assert len(issues) == 0

    def test_generic_alt_text_flagged_as_inadequate(self):
        slide = NormalizedSlide(
            slide_index=0,
            title="Slide 1",
            elements=[
                NormalizedElement(
                    element_id="s0_img0",
                    element_type="IMAGE",
                    alt_text="image",
                )
            ],
        )
        doc = make_pptx_doc(slides=[slide])
        issues = check_alt_text(doc)
        assert len(issues) == 1
        assert issues[0].issue_type == "INADEQUATE_ALT_TEXT"

    def test_filename_alt_text_flagged(self):
        slide = NormalizedSlide(
            slide_index=0,
            title="Slide 1",
            elements=[
                NormalizedElement(
                    element_id="s0_img0",
                    element_type="IMAGE",
                    alt_text="image1.png",
                )
            ],
        )
        doc = make_pptx_doc(slides=[slide])
        issues = check_alt_text(doc)
        assert len(issues) == 1
        assert issues[0].issue_type == "INADEQUATE_ALT_TEXT"


# ── Structure Checker ────────────────────────────────────────────────────────

class TestStructureChecker:
    def test_missing_slide_title_flagged(self):
        slide = NormalizedSlide(slide_index=0, title=None, elements=[])
        doc = make_pptx_doc(slides=[slide])
        issues = check_structure(doc)
        assert len(issues) == 1
        assert issues[0].issue_type == "MISSING_SLIDE_TITLE"
        assert issues[0].severity == "SERIOUS"

    def test_empty_slide_title_flagged(self):
        slide = NormalizedSlide(slide_index=0, title="", elements=[])
        doc = make_pptx_doc(slides=[slide])
        issues = check_structure(doc)
        assert any(i.issue_type == "MISSING_SLIDE_TITLE" for i in issues)

    def test_present_slide_title_not_flagged(self):
        slide = NormalizedSlide(slide_index=0, title="Introduction to Biology", elements=[])
        doc = make_pptx_doc(slides=[slide])
        issues = check_structure(doc)
        assert len(issues) == 0


# ── PDF Tag Checker ───────────────────────────────────────────────────────────

class TestPdfTagChecker:
    def test_untagged_pdf_flagged(self):
        doc = make_pdf_doc(is_tagged_pdf=False, has_pdf_language=True, pages=[])
        issues = check_pdf_tags(doc)
        types = [i.issue_type for i in issues]
        assert "UNTAGGED_PDF" in types
        assert "MISSING_LANGUAGE" not in types

    def test_missing_language_flagged(self):
        doc = make_pdf_doc(is_tagged_pdf=True, has_pdf_language=False, pages=[])
        issues = check_pdf_tags(doc)
        types = [i.issue_type for i in issues]
        assert "MISSING_LANGUAGE" in types
        assert "UNTAGGED_PDF" not in types

    def test_tagged_pdf_with_language_clean(self):
        doc = make_pdf_doc(is_tagged_pdf=True, has_pdf_language=True, pages=[])
        issues = check_pdf_tags(doc)
        assert len(issues) == 0


# ── Caption Checker ───────────────────────────────────────────────────────────

class TestCaptionChecker:
    def test_missing_captions_flagged(self):
        from app.processing.normalizers import NormalizedMedia
        doc = NormalizedDocument(
            asset_id="test",
            source_type="MP4",
            media=NormalizedMedia(has_embedded_captions=False, segments=[]),
        )
        issues = check_captions(doc)
        assert len(issues) == 1
        assert issues[0].issue_type == "MISSING_CAPTIONS"
        assert issues[0].auto_fixable is True

    def test_embedded_captions_not_flagged(self):
        from app.processing.normalizers import NormalizedMedia
        doc = NormalizedDocument(
            asset_id="test",
            source_type="MP4",
            media=NormalizedMedia(has_embedded_captions=True),
        )
        issues = check_captions(doc)
        assert len(issues) == 0


# ── Contrast calculation ──────────────────────────────────────────────────────

class TestContrastRatio:
    def test_black_on_white_high_contrast(self):
        ratio = _contrast_ratio((0, 0, 0), (255, 255, 255))
        assert ratio == pytest.approx(21.0, rel=0.01)

    def test_white_on_white_no_contrast(self):
        ratio = _contrast_ratio((255, 255, 255), (255, 255, 255))
        assert ratio == pytest.approx(1.0, rel=0.01)

    def test_mid_gray_borderline(self):
        ratio = _contrast_ratio((118, 118, 118), (255, 255, 255))
        # Should be around 4.5:1 (borderline WCAG AA pass)
        assert 4.0 < ratio < 5.0
