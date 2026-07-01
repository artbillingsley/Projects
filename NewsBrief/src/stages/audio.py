# src/stages/audio.py
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, List

from src.lib.elevenlabs import SlotAudio, generate_slot_audio
from src.lib.pronunciation import GateResult, PronunciationDict, check_proper_noun_gate, inject_ssml
from src.stages.script import ScriptResult


@dataclass
class AudioResult:
    slots: List[SlotAudio]
    gate_result: GateResult
    total_characters: int
    total_duration_seconds: float


def generate_all_audio(
    script: ScriptResult,
    el_client: Any,
    voice_id: str,
    pronunciation: PronunciationDict,
    output_dir: str,
) -> AudioResult:
    """Orchestrate 5 ElevenLabs TTS calls (one per slot), run the
    proper-noun gate, and write audio files to disk.

    Slots generated (in order):
        HOOK, LEAD, SCAN, WHY, CLOSE

    Each slot's audio is written to ``{output_dir}/{slot_name.lower()}.mp3``.
    """
    # 1. Run the proper-noun gate on HOOK + LEAD text first
    gate_result = check_proper_noun_gate(script.hook, script.lead, pronunciation)

    # 2. Build text for each of the 5 slots with SSML pronunciation injection
    scan_text = script.scan_intro + " " + " ".join(script.scan_items)
    slot_texts = [
        ("HOOK", inject_ssml(script.hook, pronunciation)),
        ("LEAD", inject_ssml(script.lead, pronunciation)),
        ("SCAN", inject_ssml(scan_text, pronunciation)),
        ("WHY", inject_ssml(script.why, pronunciation)),
        ("CLOSE", inject_ssml(script.close, pronunciation)),
    ]

    # 3. Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # 4. Call ElevenLabs with clean text, write files
    slots: List[SlotAudio] = []
    for slot_name, raw_text in slot_texts:
        slot_audio = generate_slot_audio(el_client, voice_id, raw_text, slot_name)
        out_path = os.path.join(output_dir, f"{slot_name.lower()}.mp3")
        with open(out_path, "wb") as fh:
            fh.write(slot_audio.audio_bytes)
        slots.append(slot_audio)

    # 5. Aggregate totals
    total_characters = sum(s.character_count for s in slots)
    total_duration_seconds = sum(s.duration_seconds for s in slots)

    return AudioResult(
        slots=slots,
        gate_result=gate_result,
        total_characters=total_characters,
        total_duration_seconds=total_duration_seconds,
    )
