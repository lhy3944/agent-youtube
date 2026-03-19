"""
답변 및 요약 생성 서비스.

주요 기능:
- 검색된 자막 세그먼트를 근거로 LLM이 답변을 생성한다
- 답변에는 반드시 Citation(근거 구간)이 포함된다
- 영상 내용에 없는 정보는 추측하지 않고 불확실성을 명시한다
- 영상 전체 자막을 기반으로 요약을 생성한다

LLM 응답 형식:
  JSON { "answer": "...", "cited_segments": [1, 2, 3] }
  cited_segments는 컨텍스트에 포함된 세그먼트의 1-based 인덱스이다.
"""

import json
import logging

from openai import AsyncOpenAI

from app.core.config import settings
from app.models.transcript_segment import TranscriptSegment

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    """OpenAI 클라이언트 싱글턴 인스턴스를 반환한다."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def _format_timecode(seconds: float) -> str:
    """초 단위 시간을 사람이 읽기 쉬운 타임코드(M:SS 또는 H:MM:SS)로 변환한다."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _build_context(segments: list[TranscriptSegment]) -> str:
    """검색된 세그먼트를 LLM 프롬프트에 포함할 컨텍스트 문자열로 조합한다.

    각 세그먼트에 번호와 타임코드를 붙여 LLM이 Citation을 참조할 수 있도록 한다.
    """
    parts = []
    for i, seg in enumerate(segments):
        timecode = f"[{_format_timecode(seg.start_sec)} - {_format_timecode(seg.end_sec)}]"
        parts.append(f"[Segment {i+1}] {timecode}\n{seg.text}")
    return "\n\n".join(parts)


# LLM 시스템 프롬프트: 영상 자막 기반 답변 생성 규칙
SYSTEM_PROMPT = """You are a helpful assistant that answers questions based ONLY on the provided video transcript segments.

Rules:
1. Only use information from the provided transcript segments to answer.
2. Always include citations referencing the specific segments used, with their timestamps.
3. If the answer cannot be found in the provided segments, clearly state that the information is not available in the video content.
4. When uncertain, express uncertainty rather than guessing.
5. Respond in the same language as the user's question.

For each citation, use the format: [Segment N, timestamp]

Return your answer as JSON with this structure:
{
  "answer": "Your answer text with inline citations like [Segment 1, 0:30-1:05]",
  "cited_segments": [1, 2, 3]
}"""


async def generate_answer(
    question: str,
    segments: list[TranscriptSegment],
    chat_history: list[dict] | None = None,
) -> dict:
    """검색된 세그먼트를 근거로 질문에 대한 답변을 생성한다.

    Args:
        question: 사용자 질문
        segments: 벡터 검색으로 찾은 관련 세그먼트 목록
        chat_history: 이전 대화 히스토리 (세션 내 맥락 유지용)

    Returns:
        {"answer": "답변 텍스트", "citations": [{segment_id, start_sec, end_sec, text}]}
    """
    client = _get_client()
    context = _build_context(segments)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    # 이전 대화 히스토리 포함 (최근 3회 교환 = 6개 메시지)
    if chat_history:
        for msg in chat_history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    # 검색된 세그먼트와 질문을 user 메시지로 구성
    user_content = f"""Transcript segments:
{context}

Question: {question}"""

    messages.append({"role": "user", "content": user_content})

    # JSON 형식으로 응답 요청 (response_format 지정)
    response = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=messages,
        temperature=0.3,  # 낮은 temperature로 일관된 답변 생성
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # JSON 파싱 실패 시 원문을 그대로 답변으로 사용
        parsed = {"answer": raw, "cited_segments": []}

    # LLM이 반환한 세그먼트 인덱스(1-based)를 실제 세그먼트 데이터로 매핑
    cited_indices = parsed.get("cited_segments", [])
    citations = []
    for idx in cited_indices:
        if 1 <= idx <= len(segments):
            seg = segments[idx - 1]
            citations.append({
                "segment_id": str(seg.id),
                "start_sec": seg.start_sec,
                "end_sec": seg.end_sec,
                "text": seg.text,
            })

    return {
        "answer": parsed.get("answer", raw),
        "citations": citations,
    }


async def generate_summary(segments: list[TranscriptSegment]) -> str | None:
    """영상 전체 자막을 기반으로 요약을 생성한다.

    모든 세그먼트의 텍스트를 시간순으로 결합하여 LLM에 전달한다.
    텍스트가 30,000자를 초과하면 잘라낸다.

    Returns:
        요약 텍스트 또는 실패 시 None (요약 실패가 전체 처리를 차단하지 않음)
    """
    if not segments:
        return None

    client = _get_client()

    # 각 세그먼트에 타임코드를 붙여 전체 전사 텍스트 구성
    full_text_parts = []
    for seg in segments:
        timecode = _format_timecode(seg.start_sec)
        full_text_parts.append(f"[{timecode}] {seg.text}")
    full_text = "\n".join(full_text_parts)

    # 매우 긴 영상의 경우 텍스트를 잘라서 비용 절감
    if len(full_text) > 30000:
        full_text = full_text[:30000] + "\n... (truncated)"

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant. Summarize the following video transcript concisely. "
            "Highlight key points, main arguments, and conclusions. "
            "Respond in the same language as the transcript.",
        },
        {"role": "user", "content": full_text},
    ]

    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        return None
