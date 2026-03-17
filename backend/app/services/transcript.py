import logging

from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger(__name__)


def fetch_captions(video_id: str, preferred_lang: str = "ko") -> list[dict] | None:
    """Fetch YouTube captions using youtube-transcript-api.

    Returns list of {text, start, duration} or None on failure.
    """
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id, languages=[preferred_lang, "en"])
        segments = []
        for entry in transcript.snippets:
            segments.append({
                "text": entry.text,
                "start": entry.start,
                "duration": entry.duration,
            })
        return segments
    except Exception as e:
        logger.warning(f"Caption fetch failed for {video_id}: {e}")
        return None


def normalize_transcript(raw_segments: list[dict]) -> list[dict]:
    """Normalize raw transcript segments into standardized format.

    Returns list of {start_sec, end_sec, text}.
    """
    normalized = []
    for seg in raw_segments:
        text = seg["text"].strip()
        if not text:
            continue
        # Remove common artifacts
        text = text.replace("\n", " ").replace("[음악]", "").replace("[Music]", "").strip()
        if not text:
            continue
        start = float(seg["start"])
        duration = float(seg.get("duration", 0))
        normalized.append({
            "start_sec": start,
            "end_sec": start + duration,
            "text": text,
        })
    return normalized
