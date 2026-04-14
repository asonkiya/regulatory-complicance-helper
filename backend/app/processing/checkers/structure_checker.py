"""
Checks for missing slide titles (PPTX) and missing heading structure (PDF).
"""
from app.processing.checkers import IssueResult
from app.processing.normalizers import NormalizedDocument


def check_structure(doc: NormalizedDocument) -> list[IssueResult]:
    issues = []

    if doc.source_type == "PPTX":
        for slide in doc.slides:
            if not slide.title:
                issues.append(IssueResult(
                    issue_type="MISSING_SLIDE_TITLE",
                    severity="SERIOUS",
                    location_in_asset={"slide": slide.slide_index},
                    fix_recommendation=f"Add a descriptive title to slide {slide.slide_index + 1}.",
                    auto_fixable=False,
                ))

    elif doc.source_type == "PDF":
        # Heuristic: detect text blocks that look like headings but aren't semantically tagged.
        # Only flag for untagged PDFs — tagged PDFs handle heading structure natively.
        if doc.is_tagged_pdf:
            return issues

        for page in doc.pages:
            body_sizes = [
                b["font_size"] for b in page.text_blocks
                if b.get("font_size") and b["font_size"] > 0
            ]
            if not body_sizes:
                continue
            avg_body = sum(body_sizes) / len(body_sizes)

            candidate_headings = [
                block["text"].strip()
                for block in page.text_blocks
                if block.get("font_size")
                and block["font_size"] >= avg_body * 1.5
                and block.get("text", "").strip()
                and len(block["text"].strip()) < 150
            ]
            if candidate_headings:
                issues.append(IssueResult(
                    issue_type="MISSING_HEADING_STRUCTURE",
                    severity="SERIOUS",
                    location_in_asset={
                        "page": page.page_index,
                        "candidate_headings": candidate_headings[:5],
                    },
                    fix_recommendation=(
                        "Add semantic heading tags (H1, H2, etc.) to structure the document "
                        "so screen readers can navigate by heading."
                    ),
                    auto_fixable=False,
                ))

    return issues
