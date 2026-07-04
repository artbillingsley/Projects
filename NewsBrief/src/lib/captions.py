"""Caption generation — produces SRT and VTT subtitle files from word-level timing arrays,
and per-platform social media captions from spec data."""

from __future__ import annotations

from typing import Dict, List


def _format_srt_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS,mmm (SRT uses comma as decimal separator)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = round((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _format_vtt_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS.mmm (VTT uses period as decimal separator)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = round((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def _segment_words(words: List[Dict], max_segment_seconds: float) -> List[Dict]:
    """Group words into segments of at most max_segment_seconds each.

    Each segment dict has keys: start, end, text.
    A new segment starts when adding the next word would exceed max_segment_seconds
    from the segment's start time.
    """
    if not words:
        return []

    segments = []
    seg_start = words[0]["start"]
    seg_words = []

    for word in words:
        if seg_words and (word["end"] - seg_start) > max_segment_seconds:
            # Flush current segment
            segments.append({
                "start": seg_start,
                "end": seg_words[-1]["end"],
                "text": " ".join(w["word"] for w in seg_words),
            })
            seg_start = word["start"]
            seg_words = []
        seg_words.append(word)

    # Flush final segment
    if seg_words:
        segments.append({
            "start": seg_start,
            "end": seg_words[-1]["end"],
            "text": " ".join(w["word"] for w in seg_words),
        })

    return segments


def generate_srt(words: List[Dict], max_segment_seconds: float = 3.0) -> str:
    """Generate a full SRT subtitle string from word-level timing data.

    Args:
        words: List of dicts with keys 'word', 'start', 'end' (times in seconds).
        max_segment_seconds: Maximum duration of each subtitle segment.

    Returns:
        SRT-formatted string with numbered segments.
    """
    segments = _segment_words(words, max_segment_seconds)
    if not segments:
        return ""

    blocks = []
    for i, seg in enumerate(segments, start=1):
        start_ts = _format_srt_time(seg["start"])
        end_ts = _format_srt_time(seg["end"])
        blocks.append(f"{i}\n{start_ts} --> {end_ts}\n{seg['text']}")

    return "\n\n".join(blocks) + "\n"


def generate_vtt(words: List[Dict], max_segment_seconds: float = 3.0) -> str:
    """Generate a full WebVTT subtitle string from word-level timing data.

    Args:
        words: List of dicts with keys 'word', 'start', 'end' (times in seconds).
        max_segment_seconds: Maximum duration of each subtitle segment.

    Returns:
        WebVTT-formatted string with WEBVTT header and cue blocks.
    """
    segments = _segment_words(words, max_segment_seconds)

    header = "WEBVTT\n"
    if not segments:
        return header

    blocks = [header]
    for seg in segments:
        start_ts = _format_vtt_time(seg["start"])
        end_ts = _format_vtt_time(seg["end"])
        blocks.append(f"{start_ts} --> {end_ts}\n{seg['text']}")

    return "\n\n".join(blocks) + "\n"


# ---------------------------------------------------------------------------
# Platform caption builder
# ---------------------------------------------------------------------------

def _extract_headlines(spec: Dict) -> List[str]:
    """Pull headlines from spec slots."""
    headlines = []
    for slot in spec.get("slots", []):
        slot_type = slot.get("type", "")
        if slot_type == "LEAD":
            headlines.append(slot.get("headline", slot.get("copy", "")[:80]))
        elif slot_type == "SCAN":
            for item in slot.get("items", []):
                headlines.append(item.get("headline", item.get("copy", "")[:80]))
    return headlines


_WEBSITE_LINKS = [
    "https://www.cognoscerellc.com/news",
    "https://cifaas.cognoscerellc.com",
    "https://cognoscerellc.substack.com",
]


def _website_block() -> str:
    """Return formatted website links block."""
    return "\n".join(_WEBSITE_LINKS)


def build_caption(
    spec: Dict,
    platform: str,
    youtube_url: str = "",
) -> str:
    """Build a platform-appropriate caption from spec data."""
    date = spec.get("date", "")
    headlines = _extract_headlines(spec)
    source_names = spec.get("source_names", [])
    dot_sep = " \u00b7 "
    bid = spec.get("brief_id", "")
    label = "Tech Brief" if bid.startswith("tech-") else "Daily Brief"

    bullet_lines = "\n".join(f"\u25b6 {h}" for h in headlines)

    if platform == "instagram":
        parts = [
            f"COGNOSCERE {label} \u2014 {date}",
            "",
            bullet_lines,
            "",
        ]
        if source_names:
            parts.append(f"Sources: {dot_sep.join(source_names)}")
            parts.append("")
        if youtube_url:
            parts.append(f"\u25b6 Watch on YouTube Shorts: {youtube_url}")
            parts.append("")
        parts.append(_website_block())
        parts.append("")
        parts.append("#news #dailybrief #COGNOSCERE #newsbrief")
        return "\n".join(parts)

    if platform == "bluesky":
        # 300 char limit — lead headline + link
        lead = headlines[0] if headlines else ""
        parts = [
            f"COGNOSCERE {label} \u2014 {date}",
            "",
            lead,
        ]
        if youtube_url:
            parts.append("")
            parts.append(youtube_url)
        parts.append("")
        parts.append("https://www.cognoscerellc.com/news")
        return "\n".join(parts)[:300]

    if platform == "linkedin":
        parts = [
            f"COGNOSCERE {label} \u2014 {date}",
            "",
            "Today's top stories in under 2 minutes:",
            "",
            bullet_lines,
            "",
        ]
        if youtube_url:
            parts.append(f"\u25b6 Watch on YouTube Shorts: {youtube_url}")
            parts.append("")
        parts.append(_website_block())
        parts.append("")
        parts.append("#news #dailybrief #COGNOSCERE #newsbrief")
        return "\n".join(parts)

    if platform == "youtube":
        parts = [
            f"COGNOSCERE {label} \u2014 {date}",
            "",
            bullet_lines,
            "",
        ]
        if source_names:
            parts.append(f"Sources: {dot_sep.join(source_names)}")
            parts.append("")
        parts.append(_website_block())
        parts.append("")
        parts.append("#news #dailybrief #COGNOSCERE #newsbrief")
        return "\n".join(parts)

    # facebook and default
    parts = [
        f"COGNOSCERE {label} \u2014 {date}",
        "",
        bullet_lines,
        "",
    ]
    if source_names:
        parts.append(f"Sources: {dot_sep.join(source_names)}")
        parts.append("")
    if youtube_url:
        parts.append(f"\u25b6 Watch on YouTube Shorts: {youtube_url}")
        parts.append("")
    parts.append(_website_block())
    parts.append("")
    parts.append("#news #dailybrief #COGNOSCERE #newsbrief")
    return "\n".join(parts)
