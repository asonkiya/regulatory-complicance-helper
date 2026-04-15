"""
Checks for missing or inadequate alt text on images and charts.
"""
import re

from app.processing.checkers import IssueResult
from app.processing.normalizers import NormalizedDocument

# Patterns that indicate a generic/auto-generated filename alt text
_FILENAME_PATTERN = re.compile(r"^(image|img|picture|photo|graphic|figure|fig|chart|diagram|slide|shape|object)\d*\.(png|jpg|jpeg|gif|bmp|svg|tiff|webp)$", re.IGNORECASE)
_GENERIC_WORDS = {
    "image", "img", "picture", "photo", "graphic", "figure", "fig", "chart",
    "diagram", "slide", "shape", "object", "untitled",
}


def check_alt_text(doc: NormalizedDocument) -> list[IssueResult]:
    issues = []

    if doc.source_type == "PPTX":
        for slide in doc.slides:
            for element in slide.elements:
                if element.element_type in ("IMAGE", "CHART"):
                    issue = _check_element(element, {"slide": slide.slide_index, "element_id": element.element_id})
                    if issue:
                        issues.append(issue)

    elif doc.source_type == "PDF":
        for page in doc.pages:
            for element in page.elements:
                if element.element_type == "IMAGE":
                    location: dict = {"page": page.page_index, "element_id": element.element_id}
                    if element.bounding_box:
                        location["bbox"] = element.bounding_box
                    issue = _check_element(element, location)
                    if issue:
                        issues.append(issue)

    return issues


def _check_element(element, location: dict) -> IssueResult | None:
    alt = (element.alt_text or "").strip()

    if not alt:
        return IssueResult(
            issue_type="MISSING_ALT_TEXT",
            severity="CRITICAL",
            location_in_asset=location,
            fix_recommendation="Add descriptive alt text for this image.",
            auto_fixable=True,
        )

    if _is_inadequate(alt):
        return IssueResult(
            issue_type="INADEQUATE_ALT_TEXT",
            severity="SERIOUS",
            location_in_asset=location,
            fix_recommendation=f"Replace inadequate alt text '{alt}' with a meaningful description.",
            auto_fixable=True,
        )

    return None


def _is_inadequate(alt: str) -> bool:
    lower = alt.lower().strip()
    if lower in _GENERIC_WORDS:
        return True
    if _FILENAME_PATTERN.match(lower):
        return True
    if len(alt) < 3:
        return True
    return False
