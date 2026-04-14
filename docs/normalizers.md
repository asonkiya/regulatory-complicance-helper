# Normalizers

Normalizers convert raw uploaded files into a `NormalizedDocument` — the canonical internal format consumed by every checker and remediator. They live in `backend/app/processing/normalizers/`.

## NormalizedDocument data model

Defined in `normalizers/__init__.py`. All fields have safe `from_dict` defaults so old serialized JSON files remain readable after new fields are added.

### NormalizedDocument

```python
@dataclass
class NormalizedDocument:
    asset_id: str
    source_type: str          # "PPTX" | "PDF" | "MP4"
    slides: list[NormalizedSlide]   # populated for PPTX
    pages: list[NormalizedPage]     # populated for PDF
    media: NormalizedMedia | None   # populated for MP4
    metadata: dict[str, Any]        # source-specific stats
    # PDF-only flags
    is_tagged_pdf: bool | None
    has_pdf_language: bool | None
    has_document_title: bool | None
```

### NormalizedSlide (PPTX)

```python
@dataclass
class NormalizedSlide:
    slide_index: int          # 0-based
    title: str | None         # None if slide has no title shape
    elements: list[NormalizedElement]
```

### NormalizedPage (PDF)

```python
@dataclass
class NormalizedPage:
    page_index: int           # 0-based
    text_blocks: list[dict]   # [{text, bbox, font_size, font_name}]
    elements: list[NormalizedElement]   # images extracted from this page
    ocr_confidence: float | None        # 0.0-1.0 for scanned pages
    is_scanned: bool
    hyperlinks: list[dict]    # [{text, url, bbox, page_index}]
    tables: list[dict]        # [{bbox, row_count, col_count, has_header_row}]
```

### NormalizedElement

```python
@dataclass
class NormalizedElement:
    element_id: str           # e.g. "slide0_shape2" or "page1_img0"
    element_type: str         # IMAGE | CHART | TEXT | TABLE | TITLE | SHAPE
    text_content: str | None
    alt_text: str | None      # existing alt text, may be empty/generic
    image_path: str | None    # path to extracted image on disk
    image_bytes_b64: str | None
    bounding_box: list[float] | None   # [x0, y0, x1, y1]
    extra: dict[str, Any]     # type-specific metadata
```

The `extra` dict carries important type-specific data:
- **IMAGE (PDF):** `{"xref": int, "page_index": int}` — the PDF object xref is used by `tagged_pdf_generator` to match alt text to the correct image XObject
- **TEXT (PPTX):** `{"font_size": float, "bold": bool, "font_color": "#rrggbb"}` — used by `contrast_checker`
- **CHART:** `{"chart_title": str, "chart_xml": str}` — XML truncated to 4000 chars

### NormalizedMedia (MP4)

```python
@dataclass
class NormalizedMedia:
    has_embedded_captions: bool
    transcript_raw_path: str | None   # path to transcript_raw.json
    segments: list[dict]              # [{start: float, end: float, text: str}]
```

---

## PPTX normalizer

**File:** `normalizers/pptx_normalizer.py`  
**Entry point:** `normalize_pptx(asset_id, source_location) -> NormalizedDocument`

Opens the presentation with `python-pptx` and walks every shape on every slide:

| Shape type | What's extracted |
|---|---|
| PICTURE | Image blob saved to disk, existing alt text (cleaned for placeholders), element_id as `slide{N}_img{M}` |
| TABLE | All cell text joined as `row\|col` strings |
| CHART | Chart title + raw XML (truncated at 4000 chars) |
| TEXT_FRAME | Text content + font styles (size, bold, color hex) |

**Placeholder alt text detection:** If a shape's existing alt text matches the set `{"image", "img", "picture", "photo", "graphic", "figure", "fig", "chart", "diagram", "slide", "shape", "object", "untitled"}` or is very short (< 3 chars), `alt_text` is set to `None` so `alt_text_checker` will flag it.

**element_id format:** `slide{slide_index}_shape{shape_index}` for all shapes, `slide{slide_index}_img{img_index}` for images.

---

## PDF normalizer

**File:** `normalizers/pdf_normalizer.py`  
**Entry point:** `normalize_pdf(asset_id, source_location) -> NormalizedDocument`

### Scanned vs digital detection

Averages character count across all pages (using `pdfplumber`). If `avg_chars_per_page < 50`, the PDF is treated as scanned and Tesseract OCR is run on each page at 300 DPI (via `pymupdf` for rasterization + `pytesseract` for OCR). Scanned pages have no hyperlinks or table data.

### What gets extracted per page

| Data | Library | Notes |
|---|---|---|
| Text blocks | pdfplumber | `extract_words(extra_attrs=["fontname","size"])` — includes bbox, font size, font name |
| Images | pymupdf | Saved to disk as `page{N}_img{M}.{ext}`; xref stored in `element.extra["xref"]` |
| Hyperlinks | pdfplumber | `.annots` attribute; overlapping words used for link text |
| Tables | pdfplumber | `.find_tables()`; heuristic header detection via first-row font size |

### Document-level extraction (pikepdf)

| Field | Source |
|---|---|
| `is_tagged_pdf` | `/MarkInfo/Marked` in PDF catalog |
| `has_pdf_language` | `/Lang` in PDF catalog |
| `has_document_title` | XMP `dc:title` or DocInfo `/Title` |

### element_id format

`page{page_index}_img{img_index}` — the same element_id is stored in the database `AccessibilityIssue.location_in_asset.element_id` and used by `alt_text_generator` to find the image file on disk, and by `tagged_pdf_generator` to look up the xref for `/Alt` injection.

---

## Video normalizer

**File:** `normalizers/video_normalizer.py`  
**Entry point:** `normalize_video(asset_id, source_location) -> NormalizedDocument`

1. Runs `ffprobe` to check for embedded subtitle streams → `has_embedded_captions`
2. If no captions: extracts 16kHz mono WAV with `ffmpeg`, transcribes with `faster-whisper`
3. Saves segments as `transcript_raw.json`

**Whisper configuration:** `beam_size=5`, model size from `settings.whisper_model_size` (`base` ~1 GB, larger = more accurate/slower). The transcription queue allows only 1 concurrent worker to avoid OOM.

---

## Adding a new normalizer

1. Create `normalizers/my_type_normalizer.py` with `normalize_my_type(asset_id, source_location) -> NormalizedDocument`
2. Add a branch in `tasks/normalize_task.py` dispatching to it by `source_type`
3. If new data fields are needed, add them to `NormalizedPage` or `NormalizedDocument` with `field(default_factory=...)` defaults and update `to_dict`/`from_dict`
