"""
Checks PDF structural accessibility: tags, language, OCR quality.
"""
from app.processing.checkers import IssueResult
from app.processing.normalizers import NormalizedDocument

_LOW_OCR_THRESHOLD = 0.70  # Pages with confidence below this are flagged


def check_pdf_tags(doc: NormalizedDocument) -> list[IssueResult]:
    if doc.source_type != "PDF":
        return []

    issues = []

    if doc.is_tagged_pdf is False:
        issues.append(IssueResult(
            issue_type="UNTAGGED_PDF",
            severity="CRITICAL",
            location_in_asset={"document": True},
            fix_recommendation="PDF lacks accessibility tags. Will generate a tagged version with alt text and document structure.",
            auto_fixable=True,
        ))

    if doc.has_pdf_language is False:
        issues.append(IssueResult(
            issue_type="MISSING_LANGUAGE",
            severity="MODERATE",
            location_in_asset={"document": True},
            fix_recommendation="PDF does not specify a document language. Will add /Lang 'en-US' to the catalog.",
            auto_fixable=True,
        ))

    # Flag missing document title only for tagged PDFs (untagged PDFs are covered by UNTAGGED_PDF)
    if doc.is_tagged_pdf is True and doc.has_document_title is False:
        issues.append(IssueResult(
            issue_type="MISSING_DOCUMENT_TITLE",
            severity="MODERATE",
            location_in_asset={"document": True},
            fix_recommendation="PDF is tagged but has no document title. Will generate a descriptive title.",
            auto_fixable=True,
        ))

    # Flag low-confidence OCR pages
    for page in doc.pages:
        if page.is_scanned and page.ocr_confidence is not None:
            if page.ocr_confidence < _LOW_OCR_THRESHOLD:
                issues.append(IssueResult(
                    issue_type="LOW_OCR_CONFIDENCE",
                    severity="SERIOUS",
                    location_in_asset={"page": page.page_index},
                    fix_recommendation=(
                        f"OCR confidence on page {page.page_index + 1} is "
                        f"{page.ocr_confidence:.0%}. AI-generated alt text quality may be low. "
                        "Manual review recommended."
                    ),
                    auto_fixable=False,
                    confidence_score=page.ocr_confidence,
                ))

    return issues
