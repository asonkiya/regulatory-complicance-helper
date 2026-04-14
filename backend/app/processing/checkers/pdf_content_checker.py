"""
Checks PDF content accessibility: link text quality and table header presence.
"""
import re

from app.processing.checkers import IssueResult
from app.processing.normalizers import NormalizedDocument

# WCAG 2.4.4: link text must describe the destination, not just say "click here"
_AMBIGUOUS_LINK_TEXTS = {
    "click here", "here", "read more", "more", "link", "click",
    "this link", "this", "url", "learn more", "more info", "details",
    "info", "go", "visit", "see more",
}
_RAW_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def check_pdf_content(doc: NormalizedDocument) -> list[IssueResult]:
    if doc.source_type != "PDF":
        return []
    issues = []
    issues.extend(_check_link_text(doc))
    issues.extend(_check_table_headers(doc))
    return issues


def _check_link_text(doc: NormalizedDocument) -> list[IssueResult]:
    issues = []
    for page in doc.pages:
        for link in page.hyperlinks:
            text = link.get("text", "").strip().lower()
            text_stripped = re.sub(r"[^\w\s]", "", text).strip()
            url = link.get("url", "")

            if not text or text_stripped in _AMBIGUOUS_LINK_TEXTS or _RAW_URL_RE.match(text):
                issues.append(IssueResult(
                    issue_type="MISSING_LINK_TEXT",
                    severity="SERIOUS",
                    location_in_asset={
                        "page": page.page_index,
                        "bbox": link.get("bbox"),
                        "url": url,
                        "link_text": link.get("text", ""),
                    },
                    fix_recommendation=(
                        f"Replace the link text \"{link.get('text', '')}\" with a description of the "
                        "link destination (WCAG 2.4.4)."
                    ),
                    auto_fixable=False,
                ))
    return issues


def _check_table_headers(doc: NormalizedDocument) -> list[IssueResult]:
    issues = []
    for page in doc.pages:
        for table in page.tables:
            if not table.get("has_header_row") and table.get("row_count", 0) >= 2:
                issues.append(IssueResult(
                    issue_type="MISSING_TABLE_HEADERS",
                    severity="SERIOUS",
                    location_in_asset={
                        "page": page.page_index,
                        "table_bbox": table.get("bbox"),
                        "row_count": table.get("row_count"),
                    },
                    fix_recommendation=(
                        "Mark the first row of this table as a header row using proper "
                        "table header tags (WCAG 1.3.1)."
                    ),
                    auto_fixable=False,
                    confidence_score=0.75,
                ))
    return issues
