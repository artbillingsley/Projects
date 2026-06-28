# tests/test_audio.py
from unittest.mock import MagicMock, patch
import pytest


def _mock_slot_audio(slot_name, text):
    from src.lib.elevenlabs import SlotAudio
    return SlotAudio(
        slot_name=slot_name,
        audio_bytes=b"fake-mp3",
        word_timings=[
            {"word": w, "start": i * 0.3, "end": (i + 1) * 0.3}
            for i, w in enumerate(text.split()[:5])
        ],
        duration_seconds=len(text.split()[:5]) * 0.3,
        character_count=len(text),
    )


def test_generate_all_audio_produces_five_slots():
    from src.stages.audio import generate_all_audio, AudioResult
    from src.stages.script import ScriptResult
    from src.lib.pronunciation import PronunciationDict

    script = ScriptResult(
        lead_cluster_id=1,
        scan_cluster_ids=[3, 4, 5],
        selection_rationale="test",
        hook="Hook text here.",
        lead="Lead text here.",
        scan_intro="Three more, fast.",
        scan_items=["One. Item one.", "Two. Item two.", "Three. Item three."],
        why="Here is the thread.",
        close="That is the brief. Decide.",
        platform_meta={},
        input_tokens=100,
        output_tokens=100,
    )

    with patch("src.stages.audio.generate_slot_audio") as mock_gen:
        mock_gen.side_effect = lambda client, voice_id, text, slot_name: _mock_slot_audio(slot_name, text)

        pronunciation = PronunciationDict()
        result = generate_all_audio(
            script=script,
            el_client=MagicMock(),
            voice_id="test-voice",
            pronunciation=pronunciation,
            output_dir="/tmp/test-audio",
        )

    assert isinstance(result, AudioResult)
    assert len(result.slots) == 5
    slot_names = [s.slot_name for s in result.slots]
    assert "HOOK" in slot_names
    assert "LEAD" in slot_names
    assert "SCAN" in slot_names
    assert "WHY" in slot_names
    assert "CLOSE" in slot_names


def test_generate_all_audio_returns_gate_result():
    from src.stages.audio import generate_all_audio
    from src.stages.script import ScriptResult
    from src.lib.pronunciation import PronunciationDict

    script = ScriptResult(
        lead_cluster_id=1, scan_cluster_ids=[3], selection_rationale="test",
        hook="Hook.", lead="Lead.", scan_intro="Intro.",
        scan_items=["One. Item."], why="Why.", close="Close.",
        platform_meta={}, input_tokens=0, output_tokens=0,
    )

    with patch("src.stages.audio.generate_slot_audio") as mock_gen:
        mock_gen.side_effect = lambda client, voice_id, text, slot_name: _mock_slot_audio(slot_name, text)

        result = generate_all_audio(
            script=script,
            el_client=MagicMock(),
            voice_id="v",
            pronunciation=PronunciationDict(),
            output_dir="/tmp/test",
        )

    assert result.gate_result is not None
    assert isinstance(result.gate_result.requires_review, bool)


def test_generate_all_audio_calculates_total_chars():
    from src.stages.audio import generate_all_audio
    from src.stages.script import ScriptResult
    from src.lib.pronunciation import PronunciationDict

    script = ScriptResult(
        lead_cluster_id=1, scan_cluster_ids=[3], selection_rationale="test",
        hook="Hello world.", lead="Test lead.", scan_intro="Intro.",
        scan_items=["One. Item."], why="Why.", close="Close.",
        platform_meta={}, input_tokens=0, output_tokens=0,
    )

    with patch("src.stages.audio.generate_slot_audio") as mock_gen:
        mock_gen.side_effect = lambda client, voice_id, text, slot_name: _mock_slot_audio(slot_name, text)

        result = generate_all_audio(
            script=script,
            el_client=MagicMock(),
            voice_id="v",
            pronunciation=PronunciationDict(),
            output_dir="/tmp/test",
        )

    assert result.total_characters > 0
