"""
YouTube 관련 서비스 모듈.

주요 기능:
- YouTube URL에서 videoId(11자리) 추출
- URL 유효성 검증
- 영상 메타데이터 조회 (oembed fallback → YouTube Data API)

지원하는 URL 형식:
- youtube.com/watch?v=xxx
- youtu.be/xxx
- youtube.com/embed/xxx
- youtube.com/shorts/xxx
"""

import re
from urllib.parse import parse_qs, urlparse

import httpx

from app.core.config import settings

# YouTube URL에서 videoId를 추출하기 위한 정규식 패턴 목록
YOUTUBE_URL_PATTERNS = [
    r"(?:youtube\.com/watch\?.*v=)([\w-]{11})",  # 일반 시청 URL
    r"(?:youtu\.be/)([\w-]{11})",  # 단축 URL
    r"(?:youtube\.com/embed/)([\w-]{11})",  # 임베드 URL
    r"(?:youtube\.com/shorts/)([\w-]{11})",  # 쇼츠 URL
]


def extract_video_id(url: str) -> str | None:
    """YouTube URL에서 11자리 videoId를 추출한다.
    정규식 매칭 실패 시 쿼리 파라미터(v=)를 파싱하여 재시도한다."""
    for pattern in YOUTUBE_URL_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # 정규식에 매칭되지 않은 경우 쿼리 파라미터에서 v 값을 직접 추출
    parsed = urlparse(url)
    if parsed.hostname and ("youtube.com" in parsed.hostname or "youtu.be" in parsed.hostname):
        qs = parse_qs(parsed.query)
        v = qs.get("v")
        if v and len(v[0]) == 11:
            return v[0]

    return None


def validate_youtube_url(url: str) -> bool:
    """URL이 유효한 YouTube 영상 URL인지 검증한다."""
    return extract_video_id(url) is not None


async def fetch_video_metadata(video_id: str) -> dict | None:
    """영상 메타데이터(제목, 채널명, 썸네일, 길이 등)를 조회한다.

    1순위: oembed API (API 키 불필요, 단 duration 제공 안 됨)
    2순위: YouTube Data API v3 (API 키 필요, 상세 정보 제공)
    """
    # oembed로 먼저 시도 (API 키 없이 기본 정보 조회 가능)
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
                    "duration_sec": None,  # oembed는 영상 길이를 제공하지 않음
                    "description": None,
                }
        except httpx.HTTPError:
            pass

    # YouTube Data API v3로 상세 메타데이터 조회 (API 키가 설정된 경우에만)
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
    """ISO 8601 기간 형식(예: PT1H2M3S)을 초 단위로 변환한다."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration)
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds
