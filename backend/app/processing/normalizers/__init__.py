"""
Canonical internal representation for normalized course materials.
All normalizers produce a NormalizedDocument; all checkers consume it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NormalizedElement:
    """A single content element within a slide/page."""

    element_id: str
    element_type: str  # IMAGE | CHART | TEXT | TABLE | TITLE | SHAPE
    text_content: str | None = None
    alt_text: str | None = None  # existing alt text (may be empty/None)
    image_path: str | None = None  # path to extracted image file
    image_bytes_b64: str | None = None  # base64-encoded image for short images
    bounding_box: list[float] | None = None  # [x0, y0, x1, y1]
    extra: dict[str, Any] = field(default_factory=dict)  # type-specific metadata

    def to_dict(self) -> dict:
        return {
            "element_id": self.element_id,
            "element_type": self.element_type,
            "text_content": self.text_content,
            "alt_text": self.alt_text,
            "image_path": self.image_path,
            "image_bytes_b64": self.image_bytes_b64,
            "bounding_box": self.bounding_box,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NormalizedElement":
        return cls(**d)


@dataclass
class NormalizedSlide:
    """One slide from a PPTX."""

    slide_index: int  # 0-based
    title: str | None
    elements: list[NormalizedElement] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "slide_index": self.slide_index,
            "title": self.title,
            "elements": [e.to_dict() for e in self.elements],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NormalizedSlide":
        return cls(
            slide_index=d["slide_index"],
            title=d["title"],
            elements=[NormalizedElement.from_dict(e) for e in d.get("elements", [])],
        )


@dataclass
class NormalizedPage:
    """One page from a PDF."""

    page_index: int  # 0-based
    text_blocks: list[dict]  # [{text, bbox, font_size, font_name}]
    elements: list[NormalizedElement] = field(default_factory=list)
    ocr_confidence: float | None = None  # None if not OCR'd; 0.0-1.0 if OCR'd
    is_scanned: bool = False
    hyperlinks: list[dict] = field(default_factory=list)  # [{text, url, bbox, page_index}]
    tables: list[dict] = field(default_factory=list)  # [{bbox, row_count, col_count, has_header_row}]

    def to_dict(self) -> dict:
        return {
            "page_index": self.page_index,
            "text_blocks": self.text_blocks,
            "elements": [e.to_dict() for e in self.elements],
            "ocr_confidence": self.ocr_confidence,
            "is_scanned": self.is_scanned,
            "hyperlinks": self.hyperlinks,
            "tables": self.tables,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NormalizedPage":
        return cls(
            page_index=d["page_index"],
            text_blocks=d.get("text_blocks", []),
            elements=[NormalizedElement.from_dict(e) for e in d.get("elements", [])],
            ocr_confidence=d.get("ocr_confidence"),
            is_scanned=d.get("is_scanned", False),
            hyperlinks=d.get("hyperlinks", []),
            tables=d.get("tables", []),
        )


@dataclass
class NormalizedMedia:
    """Audio/video transcript data from an MP4."""

    has_embedded_captions: bool = False
    transcript_raw_path: str | None = None  # path to transcript_raw.json
    segments: list[dict] = field(default_factory=list)  # [{start, end, text}]

    def to_dict(self) -> dict:
        return {
            "has_embedded_captions": self.has_embedded_captions,
            "transcript_raw_path": self.transcript_raw_path,
            "segments": self.segments,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NormalizedMedia":
        return cls(**d)


@dataclass
class NormalizedDocument:
    """
    Canonical representation of a course material file.
    Produced by normalizers; consumed by checkers and remediators.
    """

    asset_id: str
    source_type: str  # PPTX | PDF | MP4
    slides: list[NormalizedSlide] = field(default_factory=list)
    pages: list[NormalizedPage] = field(default_factory=list)
    media: NormalizedMedia | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # PDF-specific structural flags
    is_tagged_pdf: bool | None = None
    has_pdf_language: bool | None = None
    has_document_title: bool | None = None

    def to_dict(self) -> dict:
        return {
            "asset_id": self.asset_id,
            "source_type": self.source_type,
            "slides": [s.to_dict() for s in self.slides],
            "pages": [p.to_dict() for p in self.pages],
            "media": self.media.to_dict() if self.media else None,
            "metadata": self.metadata,
            "is_tagged_pdf": self.is_tagged_pdf,
            "has_pdf_language": self.has_pdf_language,
            "has_document_title": self.has_document_title,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NormalizedDocument":
        return cls(
            asset_id=d["asset_id"],
            source_type=d["source_type"],
            slides=[NormalizedSlide.from_dict(s) for s in d.get("slides", [])],
            pages=[NormalizedPage.from_dict(p) for p in d.get("pages", [])],
            media=NormalizedMedia.from_dict(d["media"]) if d.get("media") else None,
            metadata=d.get("metadata", {}),
            is_tagged_pdf=d.get("is_tagged_pdf"),
            has_pdf_language=d.get("has_pdf_language"),
            has_document_title=d.get("has_document_title"),
        )
