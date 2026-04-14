"""
Anthropic Claude API wrapper.
All AI calls in the remediation pipeline go through this service.
"""
import base64
import json
import logging
from dataclasses import dataclass

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


MODEL = "claude-sonnet-4-6"


@dataclass
class AltTextResult:
    alt_text: str
    long_description: str | None
    confidence: float


@dataclass
class ChartSummaryResult:
    summary: str
    confidence: float


@dataclass
class CleanedTranscriptResult:
    segments: list[dict]  # [{start, end, text}]
    confidence: float


@dataclass
class DocumentTitleResult:
    title: str
    confidence: float


@retry(
    retry=retry_if_exception_type(anthropic.RateLimitError),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(3),
)
def generate_alt_text(
    image_path: str,
    context: str = "",
    is_chart: bool = False,
) -> AltTextResult:
    """Generate alt text for an image or chart using Claude."""
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    ext = image_path.rsplit(".", 1)[-1].lower()
    media_type_map = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "gif": "image/gif", "webp": "image/webp",
    }
    media_type = media_type_map.get(ext, "image/png")
    image_b64 = base64.standard_b64encode(image_bytes).decode()

    if is_chart:
        system = (
            "You are an accessibility expert specializing in data visualization. "
            "Generate concise, informative alt text for charts used in university course materials. "
            "Follow WCAG 2.0 AA guidelines. Include key data trends and values."
        )
        user_text = (
            f"{'Context: ' + context + chr(10) if context else ''}"
            "Generate alt text for this chart. Include: chart type, axes, key values/trends. "
            "Respond as JSON: {\"alt_text\": \"...\", \"long_description\": \"...\", \"confidence\": 0.0}"
        )
    else:
        system = (
            "You are an accessibility expert. Generate concise, descriptive alt text "
            "for images used in university course materials. Follow WCAG 2.0 AA guidelines. "
            "Be specific and functional. Avoid starting with 'Image of' or 'Picture of'."
        )
        user_text = (
            f"{'Context: ' + context + chr(10) if context else ''}"
            "Generate alt text for this image. "
            "Respond as JSON: {\"alt_text\": \"...\", \"long_description\": null, \"confidence\": 0.0}"
        )

    response = get_client().messages.create(
        model=MODEL,
        max_tokens=512,
        system=system,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": user_text},
                ],
            }
        ],
    )

    text = response.content[0].text
    try:
        # Extract JSON from the response (Claude may include prose around it)
        start = text.find("{")
        end = text.rfind("}") + 1
        data = json.loads(text[start:end])
        return AltTextResult(
            alt_text=data.get("alt_text", ""),
            long_description=data.get("long_description"),
            confidence=float(data.get("confidence", 0.8)),
        )
    except Exception:
        logger.warning("Could not parse Claude alt text response as JSON; using raw text")
        return AltTextResult(alt_text=text[:300], long_description=None, confidence=0.6)


@retry(
    retry=retry_if_exception_type(anthropic.RateLimitError),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(3),
)
def generate_document_title(
    filename: str,
    first_page_text: str,
) -> DocumentTitleResult:
    """Generate a descriptive PDF document title using Claude."""
    system = (
        "You are an accessibility metadata expert. Generate a concise, descriptive document title "
        "for a PDF used in university course materials. The title should be 5-12 words, Title Case, "
        "without file extensions or course codes."
    )
    user_text = (
        f"Filename: {filename}\n\nFirst page text (excerpt):\n{first_page_text[:500]}\n\n"
        'Respond as JSON: {"title": "...", "confidence": 0.0}'
    )

    response = get_client().messages.create(
        model=MODEL,
        max_tokens=128,
        system=system,
        messages=[{"role": "user", "content": user_text}],
    )

    text = response.content[0].text
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        data = json.loads(text[start:end])
        return DocumentTitleResult(
            title=data.get("title", filename),
            confidence=float(data.get("confidence", 0.8)),
        )
    except Exception:
        logger.warning("Could not parse Claude title response; falling back to filename")
        return DocumentTitleResult(title=filename, confidence=0.0)


@retry(
    retry=retry_if_exception_type(anthropic.RateLimitError),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(3),
)
def clean_transcript(
    raw_segments: list[dict],
    course_title: str = "",
) -> CleanedTranscriptResult:
    """Clean a raw faster-whisper transcript using Claude."""
    raw_text = "\n".join(
        f"[{s['start']:.1f}s - {s['end']:.1f}s] {s['text']}" for s in raw_segments
    )

    system = (
        "You are an expert transcript editor for university course materials. "
        "Clean the provided transcript: fix spelling errors, correct domain-specific terminology, "
        "remove filler words ('um', 'uh', 'like'), and fix punctuation. "
        "IMPORTANT: Preserve all timestamps exactly. Return the corrected transcript as JSON."
    )

    user_text = (
        f"{'Course: ' + course_title + chr(10) if course_title else ''}"
        f"Clean this transcript:\n\n{raw_text}\n\n"
        "Respond as JSON: {\"segments\": [{\"start\": 0.0, \"end\": 1.0, \"text\": \"...\"}], \"confidence\": 0.9}"
    )

    response = get_client().messages.create(
        model=MODEL,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user_text}],
    )

    text = response.content[0].text
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        data = json.loads(text[start:end])
        return CleanedTranscriptResult(
            segments=data.get("segments", raw_segments),
            confidence=float(data.get("confidence", 0.85)),
        )
    except Exception:
        logger.warning("Could not parse Claude transcript response; returning raw segments")
        return CleanedTranscriptResult(segments=raw_segments, confidence=0.5)
