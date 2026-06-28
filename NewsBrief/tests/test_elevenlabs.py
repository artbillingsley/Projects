# tests/test_elevenlabs.py
from unittest.mock import MagicMock
import pytest


def test_generate_slot_audio_returns_audio_and_timestamps():
    from src.lib.elevenlabs import generate_slot_audio, SlotAudio

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.audio = b"fake-mp3-bytes"
    mock_response.alignment = MagicMock(
        characters=list("Iran shot"),
        character_start_times_seconds=[0.0, 0.02, 0.04, 0.06, 0.08, 0.1, 0.12, 0.14, 0.16],
        character_end_times_seconds=[0.02, 0.04, 0.06, 0.08, 0.1, 0.12, 0.14, 0.16, 0.18],
    )
    mock_client.text_to_speech.convert.return_value = mock_response

    result = generate_slot_audio(
        client=mock_client,
        voice_id="test-voice",
        text="Iran shot",
        slot_name="HOOK",
    )

    assert isinstance(result, SlotAudio)
    assert result.audio_bytes == b"fake-mp3-bytes"
    assert result.slot_name == "HOOK"
    mock_client.text_to_speech.convert.assert_called_once()


def test_generate_slot_audio_uses_correct_voice_settings():
    from src.lib.elevenlabs import generate_slot_audio

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.audio = b"bytes"
    mock_response.alignment = MagicMock(
        characters=list("Hi"),
        character_start_times_seconds=[0.0, 0.05],
        character_end_times_seconds=[0.05, 0.1],
    )
    mock_client.text_to_speech.convert.return_value = mock_response

    generate_slot_audio(
        client=mock_client,
        voice_id="v123",
        text="Hi",
        slot_name="CLOSE",
    )

    call_kwargs = mock_client.text_to_speech.convert.call_args.kwargs
    assert call_kwargs["voice_id"] == "v123"
    assert call_kwargs["output_format"] == "mp3_44100_128"


def test_chars_to_words_timing():
    from src.lib.elevenlabs import chars_to_word_timing

    chars = list("Iran shot")
    starts = [0.0, 0.02, 0.04, 0.06, 0.08, 0.1, 0.12, 0.14, 0.16]
    ends = [0.02, 0.04, 0.06, 0.08, 0.1, 0.12, 0.14, 0.16, 0.18]

    words = chars_to_word_timing(chars, starts, ends)
    assert len(words) == 2
    assert words[0]["word"] == "Iran"
    assert words[0]["start"] == 0.0
    assert words[1]["word"] == "shot"
