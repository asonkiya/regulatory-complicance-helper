"""
Generates VTT and SRT caption files from the raw transcript.
Optionally cleans the transcript with Claude first.
"""
import json
import logging
from pathlib import Path

from app.services.storage_service import get_asset_dir

logger = logging.getLogger(__name__)


def generate_captions_for_asset(asset) -> dict[str, Path] | None:
    """
    Reads transcript_raw.json, optionally cleans with Claude, then
    writes VTT and SRT files. Returns {artifact_type: path} or None.
    """
    asset_dir = get_asset_dir(str(asset.asset_id))
    raw_path = asset_dir / "transcript_raw.json"

    if not raw_path.exists():
        logger.warning("No transcript_raw.json for asset %s", asset.asset_id)
        return None

    with open(raw_path) as f:
        segments = json.load(f)

    if not segments:
        return None

    # Clean transcript with Claude if API key is set
    from app.config import settings
    clean_segments = segments
    if settings.anthropic_api_key:
        try:
            from app.services.claude_service import clean_transcript
            result = clean_transcript(segments, course_title=asset.original_filename)
            clean_segments = result.segments
            # Save cleaned transcript
            clean_path = asset_dir / "transcript_clean.json"
            with open(clean_path, "w") as f:
                json.dump(clean_segments, f, indent=2)
        except Exception:
            logger.warning("Transcript cleaning failed for asset %s; using raw", asset.asset_id)

    # Generate VTT
    vtt_path = asset_dir / "captions.vtt"
    _write_vtt(clean_segments, vtt_path)

    # Generate SRT
    srt_path = asset_dir / "captions.srt"
    _write_srt(clean_segments, srt_path)

    return {
        "CAPTIONS_VTT": vtt_path,
        "CAPTIONS_SRT": srt_path,
    }


def _write_vtt(segments: list[dict], path: Path) -> None:
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = _format_timestamp_vtt(seg["start"])
        end = _format_timestamp_vtt(seg["end"])
        text = seg["text"].strip()
        lines.append(f"{start} --> {end}")
        # Wrap at ~32 chars per WCAG guidance
        lines.extend(_wrap_text(text, 32))
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _write_srt(segments: list[dict], path: Path) -> None:
    lines = []
    for idx, seg in enumerate(segments, start=1):
        start = _format_timestamp_srt(seg["start"])
        end = _format_timestamp_srt(seg["end"])
        text = seg["text"].strip()
        lines.append(str(idx))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _format_timestamp_vtt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def _format_timestamp_srt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    ms = int((s % 1) * 1000)
    s = int(s)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _wrap_text(text: str, max_len: int) -> list[str]:
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= max_len:
            current = f"{current} {word}".strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]
