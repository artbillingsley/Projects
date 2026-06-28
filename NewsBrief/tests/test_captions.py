# tests/test_captions.py
import pytest


SAMPLE_WORDS = [
    {"word": "Iran", "start": 0.0, "end": 0.35},
    {"word": "shot", "start": 0.38, "end": 0.62},
    {"word": "down", "start": 0.65, "end": 0.89},
    {"word": "a", "start": 0.92, "end": 0.98},
    {"word": "U.S.", "start": 1.01, "end": 1.45},
    {"word": "Army", "start": 1.48, "end": 1.82},
    {"word": "Apache", "start": 1.85, "end": 2.31},
    {"word": "near", "start": 2.50, "end": 2.75},
    {"word": "the", "start": 2.78, "end": 2.90},
    {"word": "Strait", "start": 2.93, "end": 3.25},
    {"word": "of", "start": 3.28, "end": 3.35},
    {"word": "Hormuz.", "start": 3.38, "end": 4.12},
]


def test_generate_srt_produces_valid_format():
    from src.lib.captions import generate_srt

    srt = generate_srt(SAMPLE_WORDS, max_segment_seconds=3.0)
    lines = srt.strip().split("\n")
    assert lines[0] == "1"
    assert "-->" in lines[1]
    assert len(lines) >= 3


def test_generate_srt_segments_by_time():
    from src.lib.captions import generate_srt

    srt = generate_srt(SAMPLE_WORDS, max_segment_seconds=2.0)
    segment_count = srt.count("-->")
    assert segment_count >= 2


def test_generate_vtt_has_webvtt_header():
    from src.lib.captions import generate_vtt

    vtt = generate_vtt(SAMPLE_WORDS, max_segment_seconds=3.0)
    assert vtt.startswith("WEBVTT")


def test_generate_srt_handles_empty_input():
    from src.lib.captions import generate_srt

    srt = generate_srt([], max_segment_seconds=3.0)
    assert srt.strip() == ""


# ---------------------------------------------------------------------------
# Platform caption builder tests
# ---------------------------------------------------------------------------

from src.lib.captions import build_caption


def _make_spec(date="2026-06-11"):
    return {
        "date": date,
        "slots": [
            {
                "type": "LEAD",
                "headline": "Lead Headline Here",
                "copy": "Lead body copy.",
            },
            {
                "type": "SCAN",
                "items": [
                    {"headline": "Scan Item One"},
                    {"headline": "Scan Item Two"},
                    {"headline": "Scan Item Three"},
                ],
            },
        ],
    }


def test_instagram_caption_has_no_links():
    caption = build_caption(_make_spec(), platform="instagram")
    assert "http" not in caption
    assert "https" not in caption


def test_instagram_caption_has_hashtags():
    caption = build_caption(_make_spec(), platform="instagram")
    assert "#COGNOSCERE" in caption
    assert "#news" in caption


def test_instagram_caption_has_decide_signoff():
    caption = build_caption(_make_spec(), platform="instagram")
    assert "Decide." in caption


def test_instagram_caption_has_headlines():
    caption = build_caption(_make_spec(), platform="instagram")
    assert "Lead Headline Here" in caption
    assert "Scan Item One" in caption
    assert "Scan Item Three" in caption


def test_facebook_caption_includes_youtube_url():
    caption = build_caption(
        _make_spec(), platform="facebook", youtube_url="https://youtube.com/watch?v=abc123"
    )
    assert "https://youtube.com/watch?v=abc123" in caption


def test_facebook_caption_has_decide_signoff():
    caption = build_caption(_make_spec(), platform="facebook")
    assert "Decide." in caption


def test_linkedin_caption_includes_youtube_url():
    caption = build_caption(
        _make_spec(), platform="linkedin", youtube_url="https://youtube.com/watch?v=abc123"
    )
    assert "https://youtube.com/watch?v=abc123" in caption


def test_no_ai_curated_in_any_caption():
    for platform in ("instagram", "facebook", "linkedin"):
        caption = build_caption(_make_spec(), platform=platform)
        assert "AI-curated" not in caption
        assert "ai-curated" not in caption.lower()


def test_caption_includes_date():
    caption = build_caption(_make_spec(date="2026-06-11"), platform="instagram")
    assert "2026-06-11" in caption


def test_caption_includes_sources():
    spec = _make_spec()
    spec["source_names"] = ["The Guardian", "AP News"]
    caption = build_caption(spec, platform="facebook")
    assert "The Guardian" in caption


def test_unknown_platform_defaults_to_facebook():
    caption = build_caption(_make_spec(), platform="unknown")
    assert "Decide." in caption
