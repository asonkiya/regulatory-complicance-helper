"""
PDF normalizer: handles both digital PDFs (pdfplumber + pymupdf) and
scanned PDFs (Tesseract OCR via pytesseract). Also inspects PDF structure
tags using pikepdf.
"""
import logging
from pathlib import Path

import pdfplumber
import pikepdf
import pytesseract
import fitz  # pymupdf

from app.processing.normalizers import (
    NormalizedDocument,
    NormalizedElement,
    NormalizedPage,
)
from app.services.storage_service import get_asset_dir

logger = logging.getLogger(__name__)

# If average chars/page is below this, treat as scanned
_SCANNED_THRESHOLD_CHARS_PER_PAGE = 50


def normalize_pdf(asset_id: str, source_location: str) -> NormalizedDocument:
    asset_dir = get_asset_dir(asset_id)
    pages: list[NormalizedPage] = []

    # Check PDF structure tags with pikepdf
    is_tagged, has_language = _check_pdf_structure(source_location)
    has_title = _extract_document_title(source_location)

    with pdfplumber.open(source_location) as pdf:
        total_chars = sum(len(p.extract_text() or "") for p in pdf.pages)
        avg_chars = total_chars / max(len(pdf.pages), 1)
        is_scanned = avg_chars < _SCANNED_THRESHOLD_CHARS_PER_PAGE

        for page_idx, page in enumerate(pdf.pages):
            norm_page = _process_page(
                page_idx=page_idx,
                plumber_page=page,
                source_location=source_location,
                asset_dir=asset_dir,
                is_scanned=is_scanned,
            )
            pages.append(norm_page)

    return NormalizedDocument(
        asset_id=str(asset_id),
        source_type="PDF",
        pages=pages,
        is_tagged_pdf=is_tagged,
        has_pdf_language=has_language,
        has_document_title=has_title,
        metadata={
            "page_count": len(pages),
            "is_scanned": is_scanned,
            "avg_chars_per_page": round(avg_chars, 1),
        },
    )


def _check_pdf_structure(source_location: str) -> tuple[bool, bool]:
    """Return (is_tagged, has_language) by inspecting the PDF catalog."""
    try:
        with pikepdf.open(source_location) as pdf:
            catalog = pdf.Root
            # Check /MarkInfo /Marked
            mark_info = catalog.get("/MarkInfo")
            is_tagged = bool(mark_info and mark_info.get("/Marked") == True)  # noqa: E712
            # Check /Lang
            has_language = bool(catalog.get("/Lang"))
            return is_tagged, has_language
    except Exception:
        logger.warning("Could not inspect PDF structure for %s", source_location)
        return False, False


def _process_page(
    page_idx: int,
    plumber_page,
    source_location: str,
    asset_dir: Path,
    is_scanned: bool,
) -> NormalizedPage:
    text_blocks: list[dict] = []
    elements: list[NormalizedElement] = []
    ocr_confidence: float | None = None
    hyperlinks: list[dict] = []
    tables: list[dict] = []

    if is_scanned:
        # Rasterize with pymupdf and run Tesseract
        text_blocks, ocr_confidence = _ocr_page(page_idx, source_location, asset_dir)
    else:
        # Extract text blocks with layout info
        raw_words = plumber_page.extract_words(extra_attrs=["fontname", "size"]) or []
        for w in raw_words:
            text_blocks.append({
                "text": w.get("text", ""),
                "bbox": [w.get("x0"), w.get("top"), w.get("x1"), w.get("bottom")],
                "font_size": w.get("size"),
                "font_name": w.get("fontname"),
            })

        # Extract images using pymupdf
        elements = _extract_pdf_images(page_idx, source_location, asset_dir)

        # Extract hyperlinks and tables
        hyperlinks = _extract_hyperlinks(plumber_page, page_idx)
        tables = _extract_tables(plumber_page, page_idx)

    return NormalizedPage(
        page_index=page_idx,
        text_blocks=text_blocks,
        elements=elements,
        ocr_confidence=ocr_confidence,
        is_scanned=is_scanned,
        hyperlinks=hyperlinks,
        tables=tables,
    )


def _ocr_page(page_idx: int, source_location: str, asset_dir: Path) -> tuple[list[dict], float]:
    """Rasterize a PDF page at 300 DPI and run Tesseract OCR."""
    doc = fitz.open(source_location)
    page = doc[page_idx]
    mat = fitz.Matrix(300 / 72, 300 / 72)  # 300 DPI
    pix = page.get_pixmap(matrix=mat)
    doc.close()

    from PIL import Image
    import io

    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # Get full data including confidence
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

    text_blocks = []
    confidences = []
    for i, text in enumerate(data["text"]):
        text = text.strip()
        conf = int(data["conf"][i])
        if text and conf > 0:
            text_blocks.append({
                "text": text,
                "bbox": [
                    data["left"][i],
                    data["top"][i],
                    data["left"][i] + data["width"][i],
                    data["top"][i] + data["height"][i],
                ],
                "font_size": None,
                "font_name": None,
            })
            confidences.append(conf)

    avg_conf = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0
    return text_blocks, avg_conf


def _extract_pdf_images(page_idx: int, source_location: str, asset_dir: Path) -> list[NormalizedElement]:
    """Extract embedded images from a PDF page using pymupdf."""
    elements = []
    try:
        doc = fitz.open(source_location)
        page = doc[page_idx]
        for img_idx, img_ref in enumerate(page.get_images(full=True)):
            xref = img_ref[0]
            base_image = doc.extract_image(xref)
            ext = base_image.get("ext", "png")
            fname = f"page{page_idx}_img{img_idx}.{ext}"
            img_path = asset_dir / fname
            with open(img_path, "wb") as f:
                f.write(base_image["image"])

            # Get image bounding box on the page
            bbox = None
            try:
                rects = page.get_image_rects(xref)
                if rects:
                    r = rects[0]  # use first occurrence
                    bbox = [r.x0, r.y0, r.x1, r.y1]
            except Exception:
                logger.debug("Could not get image rect for xref %d on page %d", xref, page_idx)

            elements.append(NormalizedElement(
                element_id=f"page{page_idx}_img{img_idx}",
                element_type="IMAGE",
                image_path=str(img_path),
                bounding_box=bbox,
                extra={"page_index": page_idx, "xref": xref, "bbox": bbox},
            ))
        doc.close()
    except Exception:
        logger.warning("Could not extract images from page %d", page_idx)

    return elements


def _extract_document_title(source_location: str) -> bool:
    """Return True if the PDF has a non-empty document title in DocInfo or XMP metadata."""
    try:
        with pikepdf.open(source_location) as pdf:
            # Check XMP dc:title first
            try:
                with pdf.open_metadata() as meta:
                    xmp_title = meta.get("dc:title", "")
                    if xmp_title and str(xmp_title).strip():
                        return True
            except Exception:
                pass
            # Fallback: check DocInfo /Title
            title = pdf.docinfo.get("/Title", "")
            return bool(title and str(title).strip())
    except Exception:
        logger.warning("Could not read document title from %s", source_location)
        return False


def _extract_hyperlinks(plumber_page, page_idx: int) -> list[dict]:
    """
    Extract hyperlink annotations from a PDF page.
    Returns list of {text, url, bbox, page_index} dicts.
    """
    links = []
    try:
        annots = plumber_page.annots or []
        words = plumber_page.extract_words() or []

        for annot in annots:
            uri = annot.get("uri") or annot.get("data", {}).get("URI", b"")
            if not uri:
                continue
            if isinstance(uri, bytes):
                uri = uri.decode("utf-8", errors="replace")
            uri = str(uri).strip()
            if not uri:
                continue

            # Find overlapping words to get link display text
            bbox = annot.get("rect") or annot.get("bbox")
            link_text = ""
            if bbox:
                x0, y0, x1, y1 = bbox
                overlapping = [
                    w["text"] for w in words
                    if w.get("x0", 0) < x1 and w.get("x1", 0) > x0
                    and w.get("top", 0) < y1 and w.get("bottom", 0) > y0
                ]
                link_text = " ".join(overlapping).strip()

            links.append({
                "text": link_text,
                "url": uri,
                "bbox": list(bbox) if bbox else None,
                "page_index": page_idx,
            })
    except Exception:
        logger.debug("Could not extract hyperlinks from page %d", page_idx)

    return links


def _extract_tables(plumber_page, page_idx: int) -> list[dict]:
    """
    Extract table data from a PDF page using pdfplumber.
    Returns list of {bbox, row_count, col_count, has_header_row} dicts.
    """
    tables = []
    try:
        found = plumber_page.find_tables() or []
        words = plumber_page.extract_words(extra_attrs=["fontname", "size"]) or []

        # Compute average font size on the page for header heuristic
        sizes = [w.get("size", 0) for w in words if w.get("size")]
        avg_size = sum(sizes) / len(sizes) if sizes else 0

        for table in found:
            bbox = table.bbox  # (x0, top, x1, bottom)
            extracted = table.extract()
            if not extracted:
                continue
            row_count = len(extracted)
            col_count = max((len(r) for r in extracted), default=0)

            # Heuristic: check if first-row words are larger/bolder than page average
            has_header_row = False
            if row_count >= 2 and bbox and avg_size > 0:
                x0, top, x1, bottom = bbox
                # Estimate first-row bottom as top + (total height / row_count)
                row_height = (bottom - top) / row_count
                first_row_bottom = top + row_height
                first_row_sizes = [
                    w.get("size", 0) for w in words
                    if w.get("x0", 0) >= x0 and w.get("x1", 0) <= x1
                    and w.get("top", 0) >= top and w.get("bottom", 0) <= first_row_bottom
                    and w.get("size")
                ]
                if first_row_sizes:
                    first_row_avg = sum(first_row_sizes) / len(first_row_sizes)
                    has_header_row = first_row_avg >= avg_size * 1.1

            tables.append({
                "bbox": list(bbox),
                "row_count": row_count,
                "col_count": col_count,
                "has_header_row": has_header_row,
            })
    except Exception:
        logger.debug("Could not extract tables from page %d", page_idx)

    return tables
