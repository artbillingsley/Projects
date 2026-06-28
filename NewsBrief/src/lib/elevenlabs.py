# src/lib/elevenlabs.py
import base64
from dataclasses import dataclass, field
from typing import Any, Dict, List


VOICE_SETTINGS: Dict[str, float] = {
    "stability": 0.68,
    "similarity_boost": 0.80,
    "style": 0.18,
    "speed": 0.95,
}


@dataclass
class SlotAudio:
    slot_name: str
    audio_bytes: bytes
    word_timings: List[Dict[str, Any]] = field(default_factory=list)
    duration_seconds: float = 0.0
    character_count: int = 0


def chars_to_word_timing(
    chars: List[str],
    starts: List[float],
    ends: List[float],
) -> List[Dict[str, Any]]:
    """Convert character-level alignment arrays to word-level timing dicts."""
    words: List[Dict[str, Any]] = []
    current_chars: List[str] = []
    word_start: float = 0.0
    word_end: float = 0.0

    for i, char in enumerate(chars):
        if char == " ":
            if current_chars:
                words.append({
                    "word": "".join(current_chars),
                    "start": round(word_start, 3),
                    "end": round(word_end, 3),
                })
                current_chars = []
        else:
            if not current_chars:
                word_start = starts[i]
            current_chars.append(char)
            word_end = ends[i]

    # Flush the last word
    if current_chars:
        words.append({
            "word": "".join(current_chars),
            "start": round(word_start, 3),
            "end": round(word_end, 3),
        })

    return words


def generate_slot_audio(
    client: Any,
    voice_id: str,
    text: str,
    slot_name: str,
) -> SlotAudio:
    """Call ElevenLabs TTS with locked voice settings and return a SlotAudio."""
    from elevenlabs import VoiceSettings

    voice_settings = VoiceSettings(
        stability=VOICE_SETTINGS["stability"],
        similarity_boost=VOICE_SETTINGS["similarity_boost"],
        style=VOICE_SETTINGS["style"],
        speed=VOICE_SETTINGS["speed"],
    )

    response = client.text_to_speech.convert_with_timestamps(
        voice_id=voice_id,
        text=text,
        model_id="eleven_multilingual_v2",
        language_code="en",
        output_format="mp3_44100_128",
        voice_settings=voice_settings,
    )

    alignment = response.alignment
    word_timings = chars_to_word_timing(
        chars=list(alignment.characters),
        starts=list(alignment.character_start_times_seconds),
        ends=list(alignment.character_end_times_seconds),
    )

    duration_seconds = (
        max(alignment.character_end_times_seconds)
        if alignment.character_end_times_seconds
        else 0.0
    )

    # Decode base64 audio to bytes
    audio_bytes = base64.b64decode(response.audio_base_64)

    return SlotAudio(
        slot_name=slot_name,
        audio_bytes=audio_bytes,
        word_timings=word_timings,
        duration_seconds=round(duration_seconds, 3),
        character_count=len(text),
    )
