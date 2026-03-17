from app.services.transcript import normalize_transcript


class TestNormalizeTranscript:
    def test_basic_normalization(self):
        raw = [
            {"text": "Hello world", "start": 0, "duration": 5},
            {"text": "Testing", "start": 5, "duration": 3},
        ]
        result = normalize_transcript(raw)
        assert len(result) == 2
        assert result[0]["text"] == "Hello world"
        assert result[0]["start_sec"] == 0
        assert result[0]["end_sec"] == 5

    def test_removes_empty_segments(self):
        raw = [
            {"text": "", "start": 0, "duration": 5},
            {"text": "   ", "start": 5, "duration": 3},
            {"text": "Valid", "start": 8, "duration": 2},
        ]
        result = normalize_transcript(raw)
        assert len(result) == 1
        assert result[0]["text"] == "Valid"

    def test_removes_music_markers(self):
        raw = [
            {"text": "[음악]", "start": 0, "duration": 5},
            {"text": "[Music]", "start": 5, "duration": 3},
            {"text": "Real content", "start": 8, "duration": 2},
        ]
        result = normalize_transcript(raw)
        assert len(result) == 1
        assert result[0]["text"] == "Real content"

    def test_handles_newlines(self):
        raw = [{"text": "Line one\nLine two", "start": 0, "duration": 5}]
        result = normalize_transcript(raw)
        assert result[0]["text"] == "Line one Line two"
