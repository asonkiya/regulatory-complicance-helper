"""
PPTX normalizer: extracts slides, shapes, images, charts, and alt text
from a PowerPoint file using python-pptx.
"""
import base64
import io
import logging
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from app.processing.normalizers import (
    NormalizedDocument,
    NormalizedElement,
    NormalizedSlide,
)
from app.services.storage_service import get_asset_dir

logger = logging.getLogger(__name__)

# Generic/meaningless alt text values that should be flagged as inadequate
_PLACEHOLDER_ALT_TEXTS = {
    "", "image", "picture", "photo", "graphic", "figure", "chart",
    "diagram", "slide", "shape", "object",
}


def normalize_pptx(asset_id: str, source_location: str) -> NormalizedDocument:
    prs = Presentation(source_location)
    asset_dir = get_asset_dir(asset_id)
    slides = []

    for slide_idx, slide in enumerate(prs.slides):
        title_text = _extract_title(slide)
        elements = []

        for shape_idx, shape in enumerate(slide.shapes):
            element_id = f"slide{slide_idx}_shape{shape_idx}"

            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                element = _process_picture(shape, element_id, asset_dir, slide_idx, shape_idx)
                elements.append(element)

            elif shape.shape_type == MSO_SHAPE_TYPE.TABLE:
                element = NormalizedElement(
                    element_id=element_id,
                    element_type="TABLE",
                    text_content=_extract_table_text(shape.table),
                    extra={"rows": shape.table.rows.__len__(), "cols": shape.table.columns.__len__()},
                )
                elements.append(element)

            elif hasattr(shape, "chart"):
                element = _process_chart(shape, element_id, slide_idx, shape_idx)
                elements.append(element)

            elif shape.has_text_frame:
                # Skip the title shape — already captured as slide title
                if shape == slide.shapes.title:
                    continue
                text = shape.text_frame.text.strip()
                if text:
                    element = NormalizedElement(
                        element_id=element_id,
                        element_type="TEXT",
                        text_content=text,
                        extra=_extract_text_style(shape),
                    )
                    elements.append(element)

        slides.append(NormalizedSlide(
            slide_index=slide_idx,
            title=title_text,
            elements=elements,
        ))

    return NormalizedDocument(
        asset_id=str(asset_id),
        source_type="PPTX",
        slides=slides,
        metadata={"slide_count": len(slides)},
    )


def _extract_title(slide) -> str | None:
    if slide.shapes.title and slide.shapes.title.has_text_frame:
        text = slide.shapes.title.text_frame.text.strip()
        return text if text else None
    return None


def _process_picture(shape, element_id: str, asset_dir: Path, slide_idx: int, shape_idx: int) -> NormalizedElement:
    existing_alt = shape.name or ""
    # python-pptx stores alt text in shape.desc (the Description field)
    desc = getattr(shape, "desc", "") or ""
    alt_text = desc.strip() if desc.strip() else None

    # Check if alt text is just a generic placeholder
    if alt_text and alt_text.lower() in _PLACEHOLDER_ALT_TEXTS:
        alt_text = None  # Treat as missing; checker will flag INADEQUATE

    # Save image to disk
    image_path = None
    try:
        ext = shape.image.ext or "png"
        fname = f"slide{slide_idx}_img{shape_idx}.{ext}"
        image_path = asset_dir / fname
        with open(image_path, "wb") as f:
            f.write(shape.image.blob)
    except Exception:
        logger.warning("Could not extract image from shape %s", element_id)

    return NormalizedElement(
        element_id=element_id,
        element_type="IMAGE",
        alt_text=alt_text,
        image_path=str(image_path) if image_path else None,
        extra={
            "original_desc": desc,
            "shape_name": shape.name,
            "slide_index": slide_idx,
        },
    )


def _process_chart(shape, element_id: str, slide_idx: int, shape_idx: int) -> NormalizedElement:
    chart = shape.chart
    chart_title = None
    if chart.has_title and chart.chart_title.has_text_frame:
        chart_title = chart.chart_title.text_frame.text.strip()

    # Extract chart XML for AI summarization
    chart_xml = shape._element.xml if hasattr(shape, "_element") else ""

    return NormalizedElement(
        element_id=element_id,
        element_type="CHART",
        text_content=chart_title,
        extra={
            "chart_type": str(chart.chart_type),
            "chart_xml": chart_xml[:4000],  # Truncate for storage
            "slide_index": slide_idx,
        },
    )


def _extract_table_text(table) -> str:
    rows = []
    for row in table.rows:
        cells = [cell.text.strip() for cell in row.cells]
        rows.append(" | ".join(cells))
    return "\n".join(rows)


def _extract_text_style(shape) -> dict:
    """Extract font size info for contrast/heading detection."""
    try:
        tf = shape.text_frame
        if tf.paragraphs and tf.paragraphs[0].runs:
            run = tf.paragraphs[0].runs[0]
            return {
                "font_size_pt": run.font.size.pt if run.font.size else None,
                "bold": run.font.bold,
                "font_color": str(run.font.color.rgb) if run.font.color and run.font.color.type else None,
            }
    except Exception:
        pass
    return {}
