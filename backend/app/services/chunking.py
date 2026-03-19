"""
자막 텍스트 청크 분할 서비스.

정규화된 자막 세그먼트를 검색에 적합한 크기의 청크로 분할한다.
인접 청크 간에 오버랩(겹침)을 두어 문맥이 끊기지 않도록 한다.

청크 분할 전략:
- 각 청크의 최대 토큰 수를 초과하지 않도록 세그먼트를 누적
- 최대 토큰 초과 시 현재까지 누적된 텍스트를 하나의 청크로 확정
- 다음 청크 시작 시 이전 청크의 마지막 부분(overlap_tokens 만큼)을 포함

이 방식으로 검색 시 문맥 단절 없이 관련 정보를 찾을 수 있다.
"""

import tiktoken

from app.core.config import settings


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """tiktoken을 사용하여 텍스트의 토큰 수를 계산한다."""
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))


def chunk_segments(
    segments: list[dict],
    max_tokens: int | None = None,
    overlap_tokens: int | None = None,
) -> list[dict]:
    """정규화된 자막 세그먼트를 토큰 기반으로 청크 분할한다.

    Args:
        segments: 정규화된 세그먼트 리스트 [{start_sec, end_sec, text}]
        max_tokens: 청크당 최대 토큰 수 (기본: settings.CHUNK_MAX_TOKENS)
        overlap_tokens: 인접 청크 간 겹침 토큰 수 (기본: settings.CHUNK_OVERLAP_TOKENS)

    Returns:
        청크 리스트 [{start_sec, end_sec, text, token_count, segment_indices}]
        - segment_indices: 이 청크에 포함된 원본 세그먼트의 인덱스 목록
    """
    max_tokens = max_tokens or settings.CHUNK_MAX_TOKENS
    overlap_tokens = overlap_tokens or settings.CHUNK_OVERLAP_TOKENS

    if not segments:
        return []

    chunks = []
    current_texts = []  # 현재 청크에 포함된 텍스트 목록
    current_start = segments[0]["start_sec"]
    current_end = segments[0]["end_sec"]
    current_tokens = 0
    current_indices = []  # 현재 청크에 포함된 세그먼트 인덱스

    for i, seg in enumerate(segments):
        seg_tokens = count_tokens(seg["text"])

        # 현재 청크에 이 세그먼트를 추가하면 최대 토큰을 초과하는 경우 → 청크 확정
        if current_tokens + seg_tokens > max_tokens and current_texts:
            chunk_text = " ".join(current_texts)
            chunks.append({
                "start_sec": current_start,
                "end_sec": current_end,
                "text": chunk_text,
                "token_count": current_tokens,
                "segment_indices": list(current_indices),
            })

            # 오버랩 구간 계산: 이전 청크의 뒤쪽에서 overlap_tokens 만큼을 다음 청크의 시작으로 가져옴
            overlap_acc = 0
            overlap_start_idx = len(current_texts)
            for j in range(len(current_texts) - 1, -1, -1):
                t = count_tokens(current_texts[j])
                if overlap_acc + t > overlap_tokens:
                    break
                overlap_acc += t
                overlap_start_idx = j

            # 오버랩 텍스트가 있으면 다음 청크의 시작 부분에 포함
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

    # 마지막 남은 텍스트를 최종 청크로 생성
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
