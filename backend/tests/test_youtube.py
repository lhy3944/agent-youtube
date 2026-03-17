from app.services.youtube import extract_video_id, validate_youtube_url, _parse_duration


class TestExtractVideoId:
    def test_standard_url(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_short_url(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_embed_url(self):
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_shorts_url(self):
        url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_url_with_params(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120s&list=PLxxx"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_invalid_url(self):
        assert extract_video_id("https://example.com") is None

    def test_empty_string(self):
        assert extract_video_id("") is None


class TestValidateYoutubeUrl:
    def test_valid(self):
        assert validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True

    def test_invalid(self):
        assert validate_youtube_url("https://example.com") is False


class TestParseDuration:
    def test_full_duration(self):
        assert _parse_duration("PT1H2M3S") == 3723

    def test_minutes_seconds(self):
        assert _parse_duration("PT5M30S") == 330

    def test_seconds_only(self):
        assert _parse_duration("PT45S") == 45

    def test_hours_only(self):
        assert _parse_duration("PT2H") == 7200

    def test_invalid(self):
        assert _parse_duration("invalid") is None
