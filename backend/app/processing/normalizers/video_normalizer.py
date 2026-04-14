"""
Video normalizer: extracts audio from MP4 and generates a raw transcript
using faster-whisper. Checks for existing embedded subtitle tracks via ffprobe.
"""
import json
import logging
import subprocess
from pathlib import Path

from app.config import settings
from app.processing.normalizers import NormalizedDocument, NormalizedMedia
from app.services.storage_service import get_asset_dir

logger = logging.getLogger(__name__)


def normalize_video(asset_id: str, source_location: str) -> NormalizedDocument:
    asset_dir = get_asset_dir(asset_id)
    has_embedded_captions = _check_embedded_captions(source_location)

    segments: list[dict] = []
    transcript_raw_path = None

    if not has_embedded_captions:
        wav_path = asset_dir / "audio.wav"
        _extract_audio(source_location, wav_path)
        segments = _transcribe(wav_path)

        transcript_raw_path = asset_dir / "transcript_raw.json"
        with open(transcript_raw_path, "w") as f:
            json.dump(segments, f, indent=2)

        logger.info("Transcribed %d segments for asset %s", len(segments), asset_id)
    else:
        logger.info("Asset %s already has embedded captions; skipping transcription", asset_id)

    media = NormalizedMedia(
        has_embedded_captions=has_embedded_captions,
        transcript_raw_path=str(transcript_raw_path) if transcript_raw_path else None,
        segments=segments,
    )

    return NormalizedDocument(
        asset_id=str(asset_id),
        source_type="MP4",
        media=media,
        metadata={"has_embedded_captions": has_embedded_captions, "segment_count": len(segments)},
    )


def _check_embedded_captions(source_location: str) -> bool:
    """Return True if the MP4 has an embedded subtitle/caption track."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_streams", source_location,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        return any(s.get("codec_type") == "subtitle" for s in streams)
    except Exception:
        logger.warning("ffprobe failed for %s; assuming no embedded captions", source_location)
        return False


def _extract_audio(source_location: str, output_path: Path) -> None:
    """Extract 16kHz mono WAV from video."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", source_location,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        timeout=300,
    )


def _transcribe(wav_path: Path) -> list[dict]:
    """Run faster-whisper transcription. Returns list of {start, end, text}."""
    from faster_whisper import WhisperModel

    model = WhisperModel(settings.whisper_model_size, device="cpu", compute_type="int8")
    segments_iter, _ = model.transcribe(str(wav_path), beam_size=5, word_timestamps=False)

    return [
        {"start": round(seg.start, 3), "end": round(seg.end, 3), "text": seg.text.strip()}
        for seg in segments_iter
    ]
