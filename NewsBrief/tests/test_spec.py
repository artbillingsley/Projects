# tests/test_spec.py
import json
from datetime import date

import pytest


def _make_slot_audio(name, duration=10.0):
    from src.lib.elevenlabs import SlotAudio
    return SlotAudio(
        slot_name=name,
        audio_bytes=b"fake",
        word_timings=[
            {"word": "test", "start": 0.0, "end": 0.5},
            {"word": "word", "start": 0.6, "end": 1.0},
        ],
        duration_seconds=duration,
        character_count=50,
    )


def test_build_spec_returns_valid_structure():
    from src.stages.spec import build_spec
    from src.stages.extract import ExtractResult, ClusterData
    from src.stages.script import ScriptResult
    from src.stages.audio import AudioResult
    from src.lib.pronunciation import GateResult

    extract_result = ExtractResult(
        brief_id="2026-06-10", issue_number="N103", brief_date=date(2026, 6, 10),
        clusters=[
            ClusterData(id="uuid-0001", cif_code="AA01", headline="Story 1", body="Body 1",
                        why_this_matters="WTM 1", what_changed=None,
                        status="DEVELOPING", confidence="High", position=1,
                        sources=["Reuters", "AP"]),
        ],
    )
    script_result = ScriptResult(
        lead_cluster_id="uuid-0001", scan_cluster_ids=["uuid-0003", "uuid-0004", "uuid-0005"],
        selection_rationale="test", hook="Hook", lead="Lead",
        scan_intro="Intro", scan_items=["One. A.", "Two. B.", "Three. C."],
        why="Why", close="Close. Decide.",
        platform_meta={"youtube_title": "Test Title"},
        input_tokens=100, output_tokens=100,
    )
    audio_result = AudioResult(
        slots=[
            _make_slot_audio("HOOK", 9.5),
            _make_slot_audio("LEAD", 38.0),
            _make_slot_audio("SCAN", 40.0),
            _make_slot_audio("WHY", 18.0),
            _make_slot_audio("CLOSE", 9.0),
        ],
        gate_result=GateResult(requires_review=False, unknown_words=[]),
        total_characters=1500,
        total_duration_seconds=114.5,
    )

    spec = build_spec(
        extract_result=extract_result,
        script_result=script_result,
        audio_result=audio_result,
        audio_dir="/tmp/2026-06-10/audio",
    )

    assert spec["brief_id"] == "2026-06-10"
    assert spec["date"] == "2026-06-10"
    assert spec["issue_number"] == "N103"
    assert len(spec["slots"]) == 5
    assert spec["slots"][0]["type"] == "HOOK"
    assert spec["slots"][0]["audio_file"] == "/tmp/2026-06-10/audio/hook.mp3"
    assert "render_targets" in spec


def test_build_spec_includes_clip_definitions():
    from src.stages.spec import build_spec
    from src.stages.extract import ExtractResult, ClusterData
    from src.stages.script import ScriptResult
    from src.stages.audio import AudioResult
    from src.lib.pronunciation import GateResult

    extract_result = ExtractResult(
        brief_id="2026-06-10", issue_number="N103", brief_date=date(2026, 6, 10), clusters=[],
    )
    script_result = ScriptResult(
        lead_cluster_id="uuid-0001", scan_cluster_ids=["uuid-0003", "uuid-0004", "uuid-0005"],
        selection_rationale="test", hook="Hook", lead="Lead",
        scan_intro="Intro", scan_items=["One. A.", "Two. B.", "Three. C."],
        why="Why", close="Close.",
        platform_meta={}, input_tokens=0, output_tokens=0,
    )
    audio_result = AudioResult(
        slots=[_make_slot_audio(n) for n in ["HOOK", "LEAD", "SCAN", "WHY", "CLOSE"]],
        gate_result=GateResult(requires_review=False, unknown_words=[]),
        total_characters=0, total_duration_seconds=50.0,
    )

    spec = build_spec(extract_result, script_result, audio_result, "/tmp/audio")

    assert "clips" in spec
    clip_ids = [c["id"] for c in spec["clips"]]
    assert "C1" in clip_ids


def test_build_spec_serializes_to_json():
    from src.stages.spec import build_spec
    from src.stages.extract import ExtractResult, ClusterData
    from src.stages.script import ScriptResult
    from src.stages.audio import AudioResult
    from src.lib.pronunciation import GateResult

    extract_result = ExtractResult(
        brief_id="2026-06-10", issue_number="N103", brief_date=date(2026, 6, 10), clusters=[],
    )
    script_result = ScriptResult(
        lead_cluster_id="uuid-0001", scan_cluster_ids=["uuid-0003"],
        selection_rationale="", hook="H", lead="L",
        scan_intro="I", scan_items=["One. A."], why="W", close="C.",
        platform_meta={}, input_tokens=0, output_tokens=0,
    )
    audio_result = AudioResult(
        slots=[_make_slot_audio(n) for n in ["HOOK", "LEAD", "SCAN", "WHY", "CLOSE"]],
        gate_result=GateResult(requires_review=False, unknown_words=[]),
        total_characters=0, total_duration_seconds=50.0,
    )

    spec = build_spec(extract_result, script_result, audio_result, "/tmp/audio")

    json_str = json.dumps(spec, indent=2)
    parsed = json.loads(json_str)
    assert parsed["brief_id"] == "2026-06-10"
