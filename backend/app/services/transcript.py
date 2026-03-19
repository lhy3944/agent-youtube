"""
자막 확보 및 정규화 서비스.

주요 기능:
- youtube-transcript-api를 사용하여 YouTube 자막을 가져온다
- 한국어(ko) 우선, 영어(en) 대체로 자막 언어를 선택한다
- 원본 자막 데이터를 {start_sec, end_sec, text} 형식으로 정규화한다
- 노이즈 텍스트([음악], [Music] 등)를 제거한다

자막 확보 실패 시 STT fallback이 호출되어야 하며,
현재 STT는 미구현 상태이다.
"""

import logging

from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger(__name__)


def fetch_captions(video_id: str, preferred_lang: str = "ko") -> list[dict] | None:
    """YouTube 자막을 가져온다.

    Args:
        video_id: YouTube 영상 ID (11자리)
        preferred_lang: 우선 자막 언어 (기본: 한국어)

    Returns:
        자막 세그먼트 리스트 [{text, start, duration}] 또는 실패 시 None
    """
    try:
        ytt_api = YouTubeTranscriptApi()
        # 한국어 → 영어 순서로 자막 확보 시도
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
    """원본 자막 세그먼트를 표준화된 형식으로 정규화한다.

    처리 내용:
    - 빈 텍스트 세그먼트 제거
    - 줄바꿈을 공백으로 대체
    - [음악], [Music] 등 노이즈 태그 제거
    - start + duration으로 end_sec 계산

    Returns:
        정규화된 세그먼트 리스트 [{start_sec, end_sec, text}]
    """
    normalized = []
    for seg in raw_segments:
        text = seg["text"].strip()
        if not text:
            continue
        # 자막에 포함된 불필요한 태그와 줄바꿈 제거
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
