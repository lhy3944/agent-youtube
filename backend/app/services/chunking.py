import tiktoken

from app.core.config import settings


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))


def chunk_segments(
    segments: list[dict],
    max_tokens: int | None = None,
    overlap_tokens: int | None = None,
) -> list[dict]:
    """Chunk normalized transcript segments into retrieval-friendly chunks.

    Each chunk maintains timestamp ranges from its constituent segments.
    Returns list of {start_sec, end_sec, text, token_count, segment_indices}.
    """
    max_tokens = max_tokens or settings.CHUNK_MAX_TOKENS
    overlap_tokens = overlap_tokens or settings.CHUNK_OVERLAP_TOKENS

    if not segments:
        return []

    chunks = []
    current_texts = []
    current_start = segments[0]["start_sec"]
    current_end = segments[0]["end_sec"]
    current_tokens = 0
    current_indices = []

    for i, seg in enumerate(segments):
        seg_tokens = count_tokens(seg["text"])

        if current_tokens + seg_tokens > max_tokens and current_texts:
            chunk_text = " ".join(current_texts)
            chunks.append({
                "start_sec": current_start,
                "end_sec": current_end,
                "text": chunk_text,
                "token_count": current_tokens,
                "segment_indices": list(current_indices),
            })

            # Find overlap start point
            overlap_acc = 0
            overlap_start_idx = len(current_texts)
            for j in range(len(current_texts) - 1, -1, -1):
                t = count_tokens(current_texts[j])
                if overlap_acc + t > overlap_tokens:
                    break
                overlap_acc += t
                overlap_start_idx = j

            if overlap_start_idx < len(current_texts):
                current_texts = current_texts[overlap_start_idx:]
                current_indices = current_indices[overlap_start_idx:]
                current_start = segments[current_indices[0]]["start_sec"]
                current_tokens = sum(count_tokens(t) for t in current_texts)
            else:
                current_texts = []
                current_indices = []
                current_start = seg["start_sec"]
                current_tokens = 0

        current_texts.append(seg["text"])
        current_indices.append(i)
        current_end = seg["end_sec"]
        current_tokens += seg_tokens

    # Final chunk
    if current_texts:
        chunk_text = " ".join(current_texts)
        chunks.append({
            "start_sec": current_start,
            "end_sec": current_end,
            "text": chunk_text,
            "token_count": count_tokens(chunk_text),
            "segment_indices": list(current_indices),
        })

    return chunks
