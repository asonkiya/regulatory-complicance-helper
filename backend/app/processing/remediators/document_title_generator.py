"""
Generates a descriptive document title for PDFs missing one.
"""
import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TitleGenResult:
    title: str
    confidence: float


def generate_title_for_issue(asset, issue) -> TitleGenResult:
    """
    Generate a document title for a PDF with MISSING_DOCUMENT_TITLE.
    Uses Claude with the filename and first-page text as context.
    """
    from app.services.claude_service import generate_document_title

    first_page_text = _extract_first_page_text(asset)

    try:
        result = generate_document_title(
            filename=asset.original_filename,
            first_page_text=first_page_text,
        )
        return TitleGenResult(title=result.title, confidence=result.confidence)
    except Exception:
        logger.exception("Claude title generation failed for asset %s", asset.asset_id)
        # Fallback: derive a readable title from the filename
        stem = Path(asset.original_filename).stem.replace("_", " ").replace("-", " ")
        return TitleGenResult(title=stem.title(), confidence=0.0)


def _extract_first_page_text(asset) -> str:
    """Load the normalized JSON and return the first page's text blocks as a string."""
    try:
        from app.processing.normalizers import NormalizedDocument

        with open(asset.normalized_content_ref) as f:
            doc = NormalizedDocument.from_dict(json.load(f))

        if doc.pages:
            return " ".join(
                b.get("text", "") for b in doc.pages[0].text_blocks if b.get("text")
            )
    except Exception:
        logger.debug("Could not read normalized doc for asset %s", asset.asset_id)
    return ""
