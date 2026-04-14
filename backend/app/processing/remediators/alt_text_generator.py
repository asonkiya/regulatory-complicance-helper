"""
Generates alt text for images and charts using Claude.
"""
import logging
from dataclasses import dataclass

from app.services.claude_service import AltTextResult, generate_alt_text

logger = logging.getLogger(__name__)


@dataclass
class AltTextGenResult:
    alt_text: str
    confidence: float


def generate_alt_text_for_issue(asset, issue) -> AltTextGenResult:
    """Generate alt text for a MISSING_ALT_TEXT or INADEQUATE_ALT_TEXT issue."""
    location = issue.location_in_asset or {}
    element_id = location.get("element_id", "")

    # Build context string from location
    if asset.source_type == "PPTX":
        slide_num = location.get("slide", 0)
        context = f"Slide {slide_num + 1} of '{asset.original_filename}'"
    elif asset.source_type == "PDF":
        page_num = location.get("page", 0)
        context = f"Page {page_num + 1} of '{asset.original_filename}'"
    else:
        context = asset.original_filename

    # Find the image path
    from app.services.storage_service import get_asset_dir
    from pathlib import Path

    asset_dir = get_asset_dir(str(asset.asset_id))

    # Try to find the image file by element_id pattern
    image_path = None
    if element_id:
        # element_id format: "slide{N}_shape{M}" or "page{N}_img{M}"
        parts = element_id.replace("slide", "").replace("shape", "_").replace("page", "").replace("img", "_").split("_")
        for ext in ("png", "jpg", "jpeg", "gif", "webp"):
            candidate = asset_dir / f"{element_id.replace('shape', 'img')}.{ext}"
            if not candidate.exists():
                # Try original element_id as-is with common image extensions
                for p in asset_dir.glob(f"*{parts[0] if parts else ''}*img*.{ext}"):
                    candidate = p
                    break
            if candidate.exists():
                image_path = candidate
                break

    if not image_path:
        # Fall back: use first image in asset dir
        for ext in ("png", "jpg", "jpeg"):
            found = list(asset_dir.glob(f"*.{ext}"))
            if found:
                image_path = found[0]
                break

    if not image_path:
        logger.warning("No image file found for issue %s", issue.issue_id)
        return AltTextGenResult(alt_text="[Image: description unavailable]", confidence=0.1)

    is_chart = (issue.issue_type in ("MISSING_ALT_TEXT",) and "CHART" in element_id.upper())

    try:
        result: AltTextResult = generate_alt_text(
            image_path=str(image_path),
            context=context,
            is_chart=is_chart,
        )
        return AltTextGenResult(alt_text=result.alt_text, confidence=result.confidence)
    except Exception as exc:
        logger.exception("Alt text generation failed for issue %s", issue.issue_id)
        return AltTextGenResult(alt_text="[Alt text generation failed]", confidence=0.0)
