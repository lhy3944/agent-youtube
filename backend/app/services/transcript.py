"""
자막 확보 및 정규화 서비스.

주요 기능:
- youtube-transcript-api를 사용하여 YouTube 자막을 가져온다
- 자막 확보 전략 (우선순위):
  1. 수동 자막: 한국어(ko) → 영어(en)
  2. 자동 생성 자막: 한국어(ko) → 영어(en)
  3. 사용 가능한 아무 자막이라도 가져오기
- 원본 자막 데이터를 {start_sec, end_sec, text} 형식으로 정규화한다
- 노이즈 텍스트([음악], [Music] 등)를 제거한다
"""

import logging

from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger(__name__)


def fetch_captions(video_id: str, preferred_lang: str = "ko") -> list[dict] | None:
    """YouTube 자막을 가져온다. 수동 자막 → 자동 생성 자막 순으로 시도한다.

    Args:
        video_id: YouTube 영상 ID (11자리)
        preferred_lang: 우선 자막 언어 (기본: 한국어)

    Returns:
        자막 세그먼트 리스트 [{text, start, duration}] 또는 실패 시 None
    """
    ytt_api = YouTubeTranscriptApi()

    # 전략 1: 지정 언어의 수동/자동 자막 직접 요청
    try:
        transcript = ytt_api.fetch(video_id, languages=[preferred_lang, "en"])
        return _extract_segments(transcript)
    except Exception as e:
        logger.info(f"Direct fetch failed for {video_id} ({preferred_lang}, en): {e}")

    # 전략 2: 사용 가능한 자막 목록을 조회하여 자동 생성 자막 포함 재시도
    try:
        transcript_list = ytt_api.list(video_id)

        # 사용 가능한 자막에서 선호 언어 순으로 찾기
        for lang in [preferred_lang, "en"]:
            for t in transcript_list:
                if t.language_code == lang:
                    transcript = t.fetch()
                    logger.info(f"Found caption for {video_id}: lang={lang}")
                    return _extract_segments(transcript)

        # 선호 언어가 없으면 아무 자막이라도 가져오기
        if transcript_list:
            first = transcript_list[0]
            transcript = first.fetch()
            logger.info(f"Using fallback caption for {video_id}: lang={first.language_code}")
            return _extract_segments(transcript)

    except Exception as e:
        logger.warning(f"Caption list/fetch failed for {video_id}: {e}")

    return None


def _extract_segments(transcript) -> list[dict]:
    """Transcript 객체에서 세그먼트를 추출한다."""
    segments = []
    for entry in transcript.snippets:
        segments.append({
            "text": entry.text,
            "start": entry.start,
            "duration": entry.duration,
        })
    return segments


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
