from unittest.mock import patch

from app.services.chunking import chunk_segments


def _mock_count_tokens(text, model="gpt-4o-mini"):
    """Approximate token count: ~4 chars per token."""
    return max(1, len(text) // 4)


@patch("app.services.chunking.count_tokens", side_effect=_mock_count_tokens)
class TestChunkSegments:
    def test_empty_segments(self, mock_ct):
        assert chunk_segments([]) == []

    def test_single_short_segment(self, mock_ct):
        segments = [{"start_sec": 0, "end_sec": 5, "text": "Hello world"}]
        chunks = chunk_segments(segments, max_tokens=100, overlap_tokens=10)
        assert len(chunks) == 1
        assert chunks[0]["text"] == "Hello world"
        assert chunks[0]["start_sec"] == 0
        assert chunks[0]["end_sec"] == 5

    def test_multiple_segments_single_chunk(self, mock_ct):
        segments = [
            {"start_sec": 0, "end_sec": 5, "text": "Hello"},
            {"start_sec": 5, "end_sec": 10, "text": "world"},
        ]
        chunks = chunk_segments(segments, max_tokens=100, overlap_tokens=10)
        assert len(chunks) == 1
        assert "Hello" in chunks[0]["text"]
        assert "world" in chunks[0]["text"]

    def test_forces_split_on_token_limit(self, mock_ct):
        segments = [
            {"start_sec": i * 10, "end_sec": (i + 1) * 10, "text": f"Word number {i} " * 20}
            for i in range(10)
        ]
        chunks = chunk_segments(segments, max_tokens=50, overlap_tokens=10)
        assert len(chunks) > 1
        for chunk in chunks:
            assert "start_sec" in chunk
            assert "end_sec" in chunk
            assert "text" in chunk
            assert chunk["token_count"] > 0

    def test_preserves_timestamps(self, mock_ct):
        segments = [
            {"start_sec": 10.5, "end_sec": 20.3, "text": "First segment"},
            {"start_sec": 20.3, "end_sec": 30.1, "text": "Second segment"},
        ]
        chunks = chunk_segments(segments, max_tokens=1000, overlap_tokens=0)
        assert chunks[0]["start_sec"] == 10.5
        assert chunks[0]["end_sec"] == 30.1
