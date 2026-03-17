import json
import logging

from openai import AsyncOpenAI

from app.core.config import settings
from app.models.transcript_segment import TranscriptSegment

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def _format_timecode(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _build_context(segments: list[TranscriptSegment]) -> str:
    parts = []
    for i, seg in enumerate(segments):
        timecode = f"[{_format_timecode(seg.start_sec)} - {_format_timecode(seg.end_sec)}]"
        parts.append(f"[Segment {i+1}] {timecode}\n{seg.text}")
    return "\n\n".join(parts)


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
    """Generate an answer based on retrieved transcript segments."""
    client = _get_client()
    context = _build_context(segments)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    if chat_history:
        for msg in chat_history[-6:]:  # Last 3 exchanges
            messages.append({"role": msg["role"], "content": msg["content"]})

    user_content = f"""Transcript segments:
{context}

Question: {question}"""

    messages.append({"role": "user", "content": user_content})

    response = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=messages,
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"answer": raw, "cited_segments": []}

    # Map cited segment indices to actual segment data
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
    """Generate a summary of the entire video from all segments."""
    if not segments:
        return None

    client = _get_client()

    full_text_parts = []
    for seg in segments:
        timecode = _format_timecode(seg.start_sec)
        full_text_parts.append(f"[{timecode}] {seg.text}")
    full_text = "\n".join(full_text_parts)

    # Truncate if too long
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
