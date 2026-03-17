import re
from urllib.parse import parse_qs, urlparse

import httpx

from app.core.config import settings

YOUTUBE_URL_PATTERNS = [
    r"(?:youtube\.com/watch\?.*v=)([\w-]{11})",
    r"(?:youtu\.be/)([\w-]{11})",
    r"(?:youtube\.com/embed/)([\w-]{11})",
    r"(?:youtube\.com/shorts/)([\w-]{11})",
]


def extract_video_id(url: str) -> str | None:
    for pattern in YOUTUBE_URL_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    parsed = urlparse(url)
    if parsed.hostname and ("youtube.com" in parsed.hostname or "youtu.be" in parsed.hostname):
        qs = parse_qs(parsed.query)
        v = qs.get("v")
        if v and len(v[0]) == 11:
            return v[0]

    return None


def validate_youtube_url(url: str) -> bool:
    return extract_video_id(url) is not None


async def fetch_video_metadata(video_id: str) -> dict | None:
    """Fetch video metadata using YouTube Data API v3 or oembed fallback."""
    # Try oembed first (no API key needed)
    oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(oembed_url)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "title": data.get("title"),
                    "channel_title": data.get("author_name"),
                    "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                    "duration_sec": None,  # oembed doesn't provide duration
                    "description": None,
                }
        except httpx.HTTPError:
            pass

    # Try YouTube Data API if key is available
    if settings.YOUTUBE_API_KEY:
        api_url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet,contentDetails",
            "id": video_id,
            "key": settings.YOUTUBE_API_KEY,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.get(api_url, params=params)
                if resp.status_code == 200:
                    items = resp.json().get("items", [])
                    if items:
                        snippet = items[0]["snippet"]
                        content = items[0]["contentDetails"]
                        return {
                            "title": snippet.get("title"),
                            "channel_title": snippet.get("channelTitle"),
                            "description": snippet.get("description"),
                            "thumbnail_url": snippet.get("thumbnails", {})
                            .get("high", {})
                            .get("url"),
                            "duration_sec": _parse_duration(content.get("duration", "")),
                        }
            except httpx.HTTPError:
                pass

    return None


def _parse_duration(iso_duration: str) -> int | None:
    """Parse ISO 8601 duration (PT1H2M3S) to seconds."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration)
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds
