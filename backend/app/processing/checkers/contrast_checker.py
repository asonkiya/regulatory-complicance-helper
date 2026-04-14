"""
Checks WCAG 2.0 AA color contrast ratios for PPTX text elements.
"""
import logging

from app.processing.checkers import IssueResult
from app.processing.normalizers import NormalizedDocument

logger = logging.getLogger(__name__)

# WCAG 2.0 AA thresholds
_NORMAL_TEXT_RATIO = 4.5
_LARGE_TEXT_RATIO = 3.0
_LARGE_TEXT_PT = 18.0  # 18pt normal or 14pt bold


def check_contrast(doc: NormalizedDocument) -> list[IssueResult]:
    if doc.source_type != "PPTX":
        return []

    issues = []
    for slide in doc.slides:
        for element in slide.elements:
            if element.element_type != "TEXT":
                continue
            extra = element.extra or {}
            font_color_hex = extra.get("font_color")
            if not font_color_hex:
                continue  # Can't determine color — skip silently

            # For MVP: check against white background (most common in slides)
            # A full implementation would resolve shape fill color
            try:
                fg = _hex_to_rgb(font_color_hex)
                bg = (255, 255, 255)  # assume white background
                ratio = _contrast_ratio(fg, bg)

                font_size = extra.get("font_size_pt") or 12.0
                bold = extra.get("bold") or False
                is_large = font_size >= _LARGE_TEXT_PT or (font_size >= 14.0 and bold)
                threshold = _LARGE_TEXT_RATIO if is_large else _NORMAL_TEXT_RATIO

                if ratio < threshold:
                    issues.append(IssueResult(
                        issue_type="LOW_CONTRAST",
                        severity="SERIOUS",
                        location_in_asset={"slide": slide.slide_index, "element_id": element.element_id},
                        fix_recommendation=(
                            f"Contrast ratio {ratio:.2f}:1 is below WCAG AA minimum of {threshold}:1. "
                            f"Darken the text or use a higher-contrast color."
                        ),
                        auto_fixable=False,
                        confidence_score=0.9,
                    ))
            except Exception:
                issues.append(IssueResult(
                    issue_type="CONTRAST_UNVERIFIABLE",
                    severity="MINOR",
                    location_in_asset={"slide": slide.slide_index, "element_id": element.element_id},
                    fix_recommendation="Could not resolve element color. Manually verify contrast ratio meets WCAG AA.",
                    auto_fixable=False,
                ))

    return issues


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _linearize(c: int) -> float:
    s = c / 255.0
    return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4


def _luminance(r: int, g: int, b: int) -> float:
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def _contrast_ratio(fg: tuple, bg: tuple) -> float:
    l1 = _luminance(*fg)
    l2 = _luminance(*bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)
