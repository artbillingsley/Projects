# NewsBrief Plan B: Audio + Spec Implementation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate per-slot audio via ElevenLabs with SSML pronunciation injection, extract word-level timestamps, apply the proper-noun gate, post-process audio, and build the Remotion JSON spec that drives all downstream rendering.

**Architecture:** Three new stage modules (audio, spec) plus two library modules (elevenlabs client, pronunciation engine). Audio stage makes 5 ElevenLabs API calls (one per slot), transforms character-level timestamps to word-level, normalizes loudness via FFmpeg. Spec stage assembles everything into the JSON contract that Remotion consumes. Proper-noun gate (R8) sets `requires_review` flag when unknown names appear in HOOK/LEAD.

**Tech Stack:** Python 3.11+, elevenlabs SDK, pydub, ffmpeg-python, PyYAML, pytest, pytest-mock

**Depends on:** Plan A (config, models, extract result, script result, format_speech)

---

## File Structure

```
src/
  stages/
    audio.py                  # Stage 3: ElevenLabs calls, timestamp extraction, post-processing
    spec.py                   # Stage 4: Build Remotion JSON spec from all prior stages
  lib/
    elevenlabs.py             # ElevenLabs API client wrapper
    pronunciation.py          # YAML dictionary loader, SSML injection, proper-noun gate
    captions.py               # SRT/VTT generation from word timestamps (R9)
tests/
  test_pronunciation.py
  test_elevenlabs.py
  test_audio.py
  test_captions.py
  test_spec.py
```

---

### Task 1: Pronunciation Engine

**Files:**
- Create: `src/lib/pronunciation.py`
- Create: `tests/test_pronunciation.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pronunciation.py
import pytest
from pathlib import Path


SAMPLE_YAML = """
proper_nouns:
  Hormuz: '<phoneme alphabet="ipa" ph="hɔːɹˈmuːz">Hormuz</phoneme>'
  COGNOSCERE: '<phoneme alphabet="ipa" ph="kɒɡˈnɒʃɛɹeɪ">COGNOSCERE</phoneme>'

acronyms:
  speak_as_word:
    - NATO
    - CENTCOM
  spell_out:
    - ICE
    - SEC
"""


def test_load_dictionary(tmp_path):
    from src.lib.pronunciation import load_dictionary

    yaml_file = tmp_path / "pronunciation.yaml"
    yaml_file.write_text(SAMPLE_YAML)

    d = load_dictionary(str(yaml_file))
    assert "Hormuz" in d.proper_nouns
    assert "NATO" in d.speak_as_word
    assert "ICE" in d.spell_out


def test_inject_ssml_replaces_known_nouns(tmp_path):
    from src.lib.pronunciation import load_dictionary, inject_ssml

    yaml_file = tmp_path / "pronunciation.yaml"
    yaml_file.write_text(SAMPLE_YAML)
    d = load_dictionary(str(yaml_file))

    text = "Iran struck near the Strait of Hormuz."
    result = inject_ssml(text, d)
    assert '<phoneme alphabet="ipa"' in result
    assert "Hormuz" not in result.split('<phoneme')[0].split('</phoneme>')[-1] or "hɔːɹˈmuːz" in result


def test_inject_ssml_leaves_unknown_words_alone(tmp_path):
    from src.lib.pronunciation import load_dictionary, inject_ssml

    yaml_file = tmp_path / "pronunciation.yaml"
    yaml_file.write_text(SAMPLE_YAML)
    d = load_dictionary(str(yaml_file))

    text = "Biden spoke to reporters."
    result = inject_ssml(text, d)
    assert result == text


def test_find_unknown_proper_nouns(tmp_path):
    from src.lib.pronunciation import load_dictionary, find_unknown_proper_nouns

    yaml_file = tmp_path / "pronunciation.yaml"
    yaml_file.write_text(SAMPLE_YAML)
    d = load_dictionary(str(yaml_file))

    # Simulate cluster headlines with proper nouns
    words_in_script = ["Hormuz", "Netanyahu", "Pulte", "CENTCOM"]
    unknown = find_unknown_proper_nouns(words_in_script, d)
    assert "Netanyahu" in unknown
    assert "Pulte" in unknown
    assert "Hormuz" not in unknown  # known
    assert "CENTCOM" not in unknown  # known (speak_as_word)


def test_proper_noun_gate_flags_unknown_in_hook(tmp_path):
    from src.lib.pronunciation import load_dictionary, check_proper_noun_gate

    yaml_file = tmp_path / "pronunciation.yaml"
    yaml_file.write_text(SAMPLE_YAML)
    d = load_dictionary(str(yaml_file))

    hook_text = "Netanyahu's war near Hormuz escalates."
    lead_text = "Iran struck U.S. bases."

    result = check_proper_noun_gate(hook_text, lead_text, d)
    assert result.requires_review is True
    assert "Netanyahu" in result.unknown_words


def test_proper_noun_gate_passes_when_all_known(tmp_path):
    from src.lib.pronunciation import load_dictionary, check_proper_noun_gate

    yaml_file = tmp_path / "pronunciation.yaml"
    yaml_file.write_text(SAMPLE_YAML)
    d = load_dictionary(str(yaml_file))

    hook_text = "The Strait of Hormuz is a shooting gallery."
    lead_text = "COGNOSCERE reports the latest."

    result = check_proper_noun_gate(hook_text, lead_text, d)
    assert result.requires_review is False
    assert result.unknown_words == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_pronunciation.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

```python
# src/lib/pronunciation.py
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set

import yaml
import structlog

log = structlog.get_logger()


@dataclass
class PronunciationDict:
    proper_nouns: Dict[str, str] = field(default_factory=dict)
    speak_as_word: Set[str] = field(default_factory=set)
    spell_out: Set[str] = field(default_factory=set)

    @property
    def all_known_words(self) -> Set[str]:
        return set(self.proper_nouns.keys()) | self.speak_as_word | self.spell_out


@dataclass
class GateResult:
    requires_review: bool
    unknown_words: List[str]


def load_dictionary(yaml_path: str) -> PronunciationDict:
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f) or {}

    return PronunciationDict(
        proper_nouns=data.get("proper_nouns", {}),
        speak_as_word=set(data.get("acronyms", {}).get("speak_as_word", [])),
        spell_out=set(data.get("acronyms", {}).get("spell_out", [])),
    )


def inject_ssml(text: str, dictionary: PronunciationDict) -> str:
    for word, ssml in dictionary.proper_nouns.items():
        pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        text = pattern.sub(ssml, text)
    return text


def _extract_capitalized_words(text: str) -> List[str]:
    """Extract words that look like proper nouns (capitalized, not sentence-start)."""
    words = re.findall(r'\b[A-Z][a-z]{2,}\b', text)
    # Also grab all-caps words (acronyms/names)
    words += re.findall(r'\b[A-Z]{2,}\b', text)
    return list(set(words))


def find_unknown_proper_nouns(
    candidate_words: List[str], dictionary: PronunciationDict
) -> List[str]:
    known = dictionary.all_known_words
    # Case-insensitive check
    known_lower = {w.lower() for w in known}
    return [w for w in candidate_words if w.lower() not in known_lower]


def check_proper_noun_gate(
    hook_text: str, lead_text: str, dictionary: PronunciationDict
) -> GateResult:
    combined = hook_text + " " + lead_text
    candidates = _extract_capitalized_words(combined)

    # Filter out common English words that happen to be capitalized
    common_words = {
        "The", "This", "That", "Here", "And", "But", "Not", "One", "Two",
        "Three", "Four", "Five", "Now", "Iran", "U.S.", "Army", "Central",
        "Command", "House", "President", "Congress", "Senate", "Republican",
        "Democratic", "American", "United", "States", "Wall", "Street",
        "Journal", "New", "York", "Times", "Washington", "Post",
    }
    candidates = [w for w in candidates if w not in common_words]

    unknown = find_unknown_proper_nouns(candidates, dictionary)

    if unknown:
        log.warning("pronunciation.gate.unknown_nouns", words=unknown)

    return GateResult(
        requires_review=len(unknown) > 0,
        unknown_words=unknown,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_pronunciation.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/lib/pronunciation.py tests/test_pronunciation.py
git commit -m "feat: pronunciation engine with SSML injection and proper-noun gate"
```

---

### Task 2: ElevenLabs Client Wrapper

**Files:**
- Create: `src/lib/elevenlabs.py`
- Create: `tests/test_elevenlabs.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_elevenlabs.py
from unittest.mock import MagicMock, patch
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_elevenlabs.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

```python
# src/lib/elevenlabs.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import structlog

log = structlog.get_logger()

# Locked voice settings (D18)
VOICE_SETTINGS = {
    "stability": 0.68,
    "similarity_boost": 0.80,
    "style": 0.18,
    "speed": 0.95,
}


@dataclass
class WordTiming:
    word: str
    start: float
    end: float


@dataclass
class SlotAudio:
    slot_name: str
    audio_bytes: bytes
    word_timings: List[Dict[str, Any]]
    duration_seconds: float
    character_count: int


def chars_to_word_timing(
    chars: List[str], starts: List[float], ends: List[float]
) -> List[Dict[str, Any]]:
    words = []
    current_word = ""
    word_start = 0.0

    for i, ch in enumerate(chars):
        if ch == " ":
            if current_word:
                words.append({
                    "word": current_word,
                    "start": round(word_start, 3),
                    "end": round(ends[i - 1], 3),
                })
                current_word = ""
        else:
            if not current_word:
                word_start = starts[i]
            current_word += ch

    if current_word:
        words.append({
            "word": current_word,
            "start": round(word_start, 3),
            "end": round(ends[-1], 3),
        })

    return words


def generate_slot_audio(
    client: Any,
    voice_id: str,
    text: str,
    slot_name: str,
) -> SlotAudio:
    log.info("elevenlabs.generate", slot=slot_name, chars=len(text))

    response = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
        voice_settings=VOICE_SETTINGS,
    )

    alignment = response.alignment
    word_timings = chars_to_word_timing(
        list(alignment.characters),
        list(alignment.character_start_times_seconds),
        list(alignment.character_end_times_seconds),
    )

    duration = 0.0
    if alignment.character_end_times_seconds:
        duration = max(alignment.character_end_times_seconds)

    log.info("elevenlabs.done", slot=slot_name, duration_s=round(duration, 2), words=len(word_timings))

    return SlotAudio(
        slot_name=slot_name,
        audio_bytes=response.audio,
        word_timings=word_timings,
        duration_seconds=round(duration, 3),
        character_count=len(text),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_elevenlabs.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/lib/elevenlabs.py tests/test_elevenlabs.py
git commit -m "feat: ElevenLabs client wrapper with word-level timestamp extraction"
```

---

### Task 3: Caption Generation (SRT/VTT)

**Files:**
- Create: `src/lib/captions.py`
- Create: `tests/test_captions.py`

- [ ] **Step 1: Write the failing test**

```python
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
    # Should have at least 2 segments for 4+ seconds of audio
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_captions.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

```python
# src/lib/captions.py
from __future__ import annotations

from typing import Any, Dict, List


def _format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_vtt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def _segment_words(
    words: List[Dict[str, Any]], max_segment_seconds: float
) -> List[Dict[str, Any]]:
    if not words:
        return []

    segments = []
    current_words = []
    segment_start = words[0]["start"]

    for w in words:
        elapsed = w["end"] - segment_start
        if elapsed > max_segment_seconds and current_words:
            segments.append({
                "start": segment_start,
                "end": current_words[-1]["end"],
                "text": " ".join(cw["word"] for cw in current_words),
            })
            current_words = [w]
            segment_start = w["start"]
        else:
            current_words.append(w)

    if current_words:
        segments.append({
            "start": segment_start,
            "end": current_words[-1]["end"],
            "text": " ".join(cw["word"] for cw in current_words),
        })

    return segments


def generate_srt(
    words: List[Dict[str, Any]], max_segment_seconds: float = 3.0
) -> str:
    segments = _segment_words(words, max_segment_seconds)
    if not segments:
        return ""

    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{_format_srt_time(seg['start'])} --> {_format_srt_time(seg['end'])}")
        lines.append(seg["text"])
        lines.append("")

    return "\n".join(lines)


def generate_vtt(
    words: List[Dict[str, Any]], max_segment_seconds: float = 3.0
) -> str:
    segments = _segment_words(words, max_segment_seconds)
    lines = ["WEBVTT", ""]

    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{_format_vtt_time(seg['start'])} --> {_format_vtt_time(seg['end'])}")
        lines.append(seg["text"])
        lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_captions.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/lib/captions.py tests/test_captions.py
git commit -m "feat: SRT/VTT caption generation from word-level timestamps"
```

---

### Task 4: Stage 3 — AUDIO

**Files:**
- Create: `src/stages/audio.py`
- Create: `tests/test_audio.py`

- [ ] **Step 1: Write the failing test**

```python
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
    from src.lib.pronunciation import PronunciationDict, GateResult

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

    mock_el_client = MagicMock()

    # Mock generate_slot_audio to return test data
    with patch("src.stages.audio.generate_slot_audio") as mock_gen:
        mock_gen.side_effect = lambda client, voice_id, text, slot_name: _mock_slot_audio(slot_name, text)

        pronunciation = PronunciationDict()
        result = generate_all_audio(
            script=script,
            el_client=mock_el_client,
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_audio.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

```python
# src/stages/audio.py
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, List, Optional

import structlog

from src.lib.elevenlabs import SlotAudio, generate_slot_audio
from src.lib.pronunciation import (
    GateResult,
    PronunciationDict,
    check_proper_noun_gate,
    inject_ssml,
)
from src.stages.script import ScriptResult

log = structlog.get_logger()


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
    log.info("audio.start")

    # Check proper-noun gate (R8) before generating audio
    gate_result = check_proper_noun_gate(script.hook, script.lead, pronunciation)
    if gate_result.requires_review:
        log.warning("audio.gate.requires_review", unknown_words=gate_result.unknown_words)

    # Build slot texts with SSML injection
    scan_text = script.scan_intro + " " + " ".join(script.scan_items)
    slot_texts = [
        ("HOOK", inject_ssml(script.hook, pronunciation)),
        ("LEAD", inject_ssml(script.lead, pronunciation)),
        ("SCAN", inject_ssml(scan_text, pronunciation)),
        ("WHY", inject_ssml(script.why, pronunciation)),
        ("CLOSE", inject_ssml(script.close, pronunciation)),
    ]

    # Generate audio for each slot
    slots: List[SlotAudio] = []
    total_chars = 0

    for slot_name, text in slot_texts:
        slot_audio = generate_slot_audio(
            client=el_client,
            voice_id=voice_id,
            text=text,
            slot_name=slot_name,
        )
        slots.append(slot_audio)
        total_chars += slot_audio.character_count

        # Write audio to file
        os.makedirs(output_dir, exist_ok=True)
        audio_path = os.path.join(output_dir, f"{slot_name.lower()}.mp3")
        with open(audio_path, "wb") as f:
            f.write(slot_audio.audio_bytes)

        log.info("audio.slot.saved", slot=slot_name, path=audio_path, duration_s=slot_audio.duration_seconds)

    total_duration = sum(s.duration_seconds for s in slots)

    log.info("audio.done", total_chars=total_chars, total_duration_s=round(total_duration, 2))

    return AudioResult(
        slots=slots,
        gate_result=gate_result,
        total_characters=total_chars,
        total_duration_seconds=round(total_duration, 3),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_audio.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/stages/audio.py tests/test_audio.py
git commit -m "feat: Stage 3 AUDIO — ElevenLabs per-slot generation with SSML and proper-noun gate"
```

---

### Task 5: Stage 4 — SPEC (Remotion JSON Builder)

**Files:**
- Create: `src/stages/spec.py`
- Create: `tests/test_spec.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_spec.py
import json
from datetime import date
from unittest.mock import MagicMock

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


def test_build_spec_returns_valid_json():
    from src.stages.spec import build_spec
    from src.stages.extract import ExtractResult, ClusterData
    from src.stages.script import ScriptResult
    from src.stages.audio import AudioResult
    from src.lib.pronunciation import GateResult

    extract_result = ExtractResult(
        brief_id=1, issue_number="N103", brief_date=date(2026, 6, 10),
        clusters=[
            ClusterData(id=1, headline="Story 1", body="Body 1",
                        why_this_matters="WTM 1", what_changed=None,
                        status="DEVELOPING", confidence="High", position=1,
                        sources=["Reuters", "AP"]),
        ],
    )
    script_result = ScriptResult(
        lead_cluster_id=1, scan_cluster_ids=[3, 4, 5],
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

    assert spec["brief_id"] == 1
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
        brief_id=1, issue_number="N103", brief_date=date(2026, 6, 10), clusters=[],
    )
    script_result = ScriptResult(
        lead_cluster_id=1, scan_cluster_ids=[3, 4, 5],
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
    assert "C1" in clip_ids  # Lead story clip


def test_build_spec_serializes_to_json():
    from src.stages.spec import build_spec
    from src.stages.extract import ExtractResult, ClusterData
    from src.stages.script import ScriptResult
    from src.stages.audio import AudioResult
    from src.lib.pronunciation import GateResult

    extract_result = ExtractResult(
        brief_id=1, issue_number="N103", brief_date=date(2026, 6, 10), clusters=[],
    )
    script_result = ScriptResult(
        lead_cluster_id=1, scan_cluster_ids=[3],
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

    # Must be JSON-serializable
    json_str = json.dumps(spec, indent=2)
    parsed = json.loads(json_str)
    assert parsed["brief_id"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_spec.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

```python
# src/stages/spec.py
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

import structlog

from src.stages.extract import ExtractResult
from src.stages.script import ScriptResult
from src.stages.audio import AudioResult

log = structlog.get_logger()


def _build_slot_entry(
    slot_type: str,
    copy: str,
    audio_dir: str,
    audio_slot: Any,
    gfx: Dict[str, Any] | None = None,
    extractable: bool = False,
    clip_id: str | None = None,
) -> Dict[str, Any]:
    return {
        "type": slot_type,
        "copy": copy,
        "audio_file": os.path.join(audio_dir, f"{slot_type.lower()}.mp3"),
        "words": audio_slot.word_timings,
        "duration_seconds": audio_slot.duration_seconds,
        "gfx": gfx or {},
        "extractable": extractable,
        "clip_id": clip_id,
    }


def build_spec(
    extract_result: ExtractResult,
    script_result: ScriptResult,
    audio_result: AudioResult,
    audio_dir: str,
) -> Dict[str, Any]:
    log.info("spec.start")

    # Map slot names to audio results
    audio_by_name = {s.slot_name: s for s in audio_result.slots}

    # Find lead cluster for GFX metadata
    lead_cluster = None
    for c in extract_result.clusters:
        if c.id == script_result.lead_cluster_id:
            lead_cluster = c
            break

    lead_gfx = {}
    if lead_cluster:
        lead_gfx = {
            "cif_tag": f"CIF-{lead_cluster.id}",
            "status": lead_cluster.status,
            "confidence": lead_cluster.confidence,
            "sources": lead_cluster.sources,
            "headline": lead_cluster.headline,
        }

    # Build scan items metadata
    scan_items_meta = []
    for i, (cluster_id, item_text) in enumerate(
        zip(script_result.scan_cluster_ids, script_result.scan_items)
    ):
        scan_cluster = None
        for c in extract_result.clusters:
            if c.id == cluster_id:
                scan_cluster = c
                break

        scan_items_meta.append({
            "number": i + 1,
            "copy": item_text,
            "cif_tag": f"CIF-{cluster_id}",
            "status": scan_cluster.status if scan_cluster else "NEW",
            "extractable": i > 0,  # Items 2+ are extractable as micro-clips
            "clip_id": f"C{i + 2}" if i > 0 else None,
        })

    slots = [
        _build_slot_entry(
            "HOOK", script_result.hook, audio_dir, audio_by_name["HOOK"],
            gfx={"cif_tag": lead_gfx.get("cif_tag", ""), "status": lead_gfx.get("status", "")},
        ),
        _build_slot_entry(
            "LEAD", script_result.lead, audio_dir, audio_by_name["LEAD"],
            gfx=lead_gfx, extractable=True, clip_id="C1",
        ),
        {
            "type": "SCAN",
            "intro_copy": script_result.scan_intro,
            "items": scan_items_meta,
            "audio_file": os.path.join(audio_dir, "scan.mp3"),
            "words": audio_by_name["SCAN"].word_timings,
            "duration_seconds": audio_by_name["SCAN"].duration_seconds,
        },
        _build_slot_entry(
            "WHY", script_result.why, audio_dir, audio_by_name["WHY"],
        ),
        _build_slot_entry(
            "CLOSE", script_result.close, audio_dir, audio_by_name["CLOSE"],
        ),
    ]

    # Clip definitions
    clips = [
        {
            "id": "C1",
            "title": lead_gfx.get("headline", "Lead Story"),
            "slots": ["HOOK", "LEAD_COMPRESSED", "WHY_TAIL"],
            "platform_meta": script_result.platform_meta,
        },
    ]
    # Add scan item clips
    for item in scan_items_meta:
        if item["extractable"]:
            clips.append({
                "id": item["clip_id"],
                "title": item["copy"][:60],
                "slots": [f"SCAN_ITEM_{item['number']}"],
                "platform_meta": {},
            })

    # T0 — "Today in One Breath" teaser
    clips.append({
        "id": "T0",
        "title": "Today in One Breath",
        "slots": ["HOOK"],
        "platform_meta": {},
    })

    render_targets = (
        ["anchor-16x9", "anchor-9x16"]
        + [c["id"] for c in clips]
        + ["thumbnail"]
    )

    spec = {
        "brief_id": extract_result.brief_id,
        "date": extract_result.brief_date.isoformat(),
        "issue_number": extract_result.issue_number,
        "slots": slots,
        "clips": clips,
        "render_targets": render_targets,
        "requires_review": audio_result.gate_result.requires_review,
        "unknown_words": audio_result.gate_result.unknown_words,
    }

    log.info("spec.done", render_targets=len(render_targets))
    return spec


def save_spec(spec: Dict[str, Any], output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(spec, f, indent=2)
    log.info("spec.saved", path=output_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_spec.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/stages/spec.py tests/test_spec.py
git commit -m "feat: Stage 4 SPEC — Remotion JSON spec builder with clip definitions"
```

---

### Task 6: Wire Stages 3-4 into Orchestrator

**Files:**
- Modify: `src/run.py`

- [ ] **Step 1: Update run.py to include audio and spec stages**

Replace the section after `# Stages 3-8 are implemented in Plans B, C, D` in `src/run.py` with:

```python
        # Stage 3: AUDIO
        if not args.dry_run:
            from src.lib.pronunciation import load_dictionary
            from src.stages.audio import generate_all_audio

            t0 = time.monotonic()
            pronunciation = load_dictionary(
                os.path.join(os.path.dirname(__file__), "..", "config", "pronunciation.yaml")
            )

            import elevenlabs as el_sdk
            el_client = el_sdk.ElevenLabs(api_key=config.elevenlabs_api_key)

            audio_dir = os.path.join("tmp", run_date.isoformat(), "audio")
            audio_result = generate_all_audio(
                script=script_result,
                el_client=el_client,
                voice_id=config.elevenlabs_voice_id,
                pronunciation=pronunciation,
                output_dir=audio_dir,
            )
            run.stage_audio_s = Decimal(str(round(time.monotonic() - t0, 2)))
            run.audio_duration_s = Decimal(str(audio_result.total_duration_seconds))
            run.elevenlabs_chars = audio_result.total_characters

            log.info("pipeline.audio.done", duration_s=audio_result.total_duration_seconds)

            # Stage 4: SPEC
            from src.stages.spec import build_spec, save_spec

            t0 = time.monotonic()
            spec = build_spec(
                extract_result=extract_result,
                script_result=script_result,
                audio_result=audio_result,
                audio_dir=audio_dir,
            )
            spec_path = os.path.join("tmp", run_date.isoformat(), "remotion-spec.json")
            save_spec(spec, spec_path)
            run.stage_spec_s = Decimal(str(round(time.monotonic() - t0, 2)))
            run.spec_path = spec_path

            log.info("pipeline.spec.done", path=spec_path)

            # Stages 5-8 are implemented in Plans C and D
            log.info("pipeline.plan_b_complete", message="Stages 5-8 not yet implemented.")
            run.status = "completed"
```

Also add `import os` at the top of `run.py` if not present.

- [ ] **Step 2: Run full test suite**

Run: `.venv/bin/pytest tests/ -v`
Expected: All pass

- [ ] **Step 3: Commit**

```bash
git add src/run.py
git commit -m "feat: wire stages 3-4 (audio + spec) into orchestrator"
```

---

## Plan B Completion Checklist

After all tasks are done, verify:

- [ ] `src/lib/pronunciation.py` loads YAML, injects SSML, detects unknown proper nouns, runs gate check
- [ ] `src/lib/elevenlabs.py` wraps TTS API, extracts word-level timestamps from character-level data
- [ ] `src/lib/captions.py` generates SRT and VTT from word timing arrays
- [ ] `src/stages/audio.py` generates 5 slot audio files with SSML and proper-noun gate
- [ ] `src/stages/spec.py` builds complete Remotion JSON spec with slot data, clip definitions, render targets
- [ ] `src/run.py` orchestrates stages 1-4 end-to-end
- [ ] All tests pass (~40+ tests total)

**Next:** Plan C (Remotion Renderer) consumes the JSON spec to produce video files.
