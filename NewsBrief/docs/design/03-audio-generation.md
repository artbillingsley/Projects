# Section 3: Audio Generation & Timestamp-Driven Sync

## Core Principle

The voice track is the master clock. Every visual element — headline reveal, card transition, text animation — is timed from ElevenLabs word-level timestamps. Nothing is hardcoded to a timecode. If the voice runs 0.3 seconds long on "Revolutionary Guards," the visuals stretch to match.

## 3.1 ElevenLabs Integration

### API Flow Per Run

```
Script (slot-segmented text)
    -> SSML injection (pronunciation dictionary applied)
        -> ElevenLabs API call(s)
            -> Returns: MP3 audio + word-level alignment JSON
```

### One API Call Per Slot

Five calls per run: HOOK, LEAD, SCAN, WHY, CLOSE. Reasons:
- Each slot's audio is a discrete file — micro-clip assembly is trivial (slot audio + CLOSE audio, concatenated)
- Word-level timestamps reset per call, giving clean per-slot timing arrays
- If one slot fails, re-render one segment, not the full two minutes
- Well within rate limits

### Concatenation

Happens at Remotion render stage, not audio stage. Remotion sequences the five audio files with controlled silence gaps (e.g., 0.3s between HOOK and LEAD, 0.15s hard cuts between SCAN items).

### Voice Settings (Locked Per Pipeline)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Model | eleven_multilingual_v2 | Best quality for cloned voices |
| Stability | 0.65-0.70 | Variation to avoid monotone, consistency for authority |
| Similarity boost | 0.80 | High fidelity to source voice |
| Style | 0.15-0.20 | Light expressiveness — not flat, not dramatic |
| Speed | 0.95 | Slightly under default for ~150 wpm authoritative pacing |

Tuned once during setup, then locked. Daily variation comes from script rhythm, not parameter jitter.

## 3.2 SSML Pronunciation Dictionary

Stored as `config/pronunciation.yaml` on EC2, versioned in git.

```yaml
proper_nouns:
  Hormuz: '<phoneme alphabet="ipa" ph="hormuːz">Hormuz</phoneme>'
  Netanyahu: '<phoneme alphabet="ipa" ph="netanjaːhuː">Netanyahu</phoneme>'
  Pulte: '<phoneme alphabet="ipa" ph="pʌltiː">Pulte</phoneme>'
  Shahed: '<phoneme alphabet="ipa" ph="ʃaːhed">Shahed</phoneme>'
  CENTCOM: '<phoneme alphabet="ipa" ph="sentkom">CENTCOM</phoneme>'
  Uppsala: '<phoneme alphabet="ipa" ph="upsaːlaː">Uppsala</phoneme>'
  COGNOSCERE: '<phoneme alphabet="ipa" ph="koɡnoʃɛreɪ">COGNOSCERE</phoneme>'
  CIFaaS: '<say-as interpret-as="characters">CIF</say-as>aas'

acronyms:
  speak_as_word: [NATO, FEMA, CENTCOM]
  spell_out: [ICE, SEC, IPO, NSO, FBI, CIA]
```

### Pipeline Injection Step

1. Scan for dictionary matches (case-insensitive, whole-word)
2. Wrap matches in SSML tags
3. Validate total SSML markup doesn't exceed ElevenLabs character limits
4. Log new proper nouns not in dictionary -> `pronunciation_review.log` for human review
5. **Proper-noun gate (R8):** If any unknown proper noun appears in HOOK or LEAD slots, set `requires_review = true` on the run. In `gate` or `auto` publish mode, this routes to the operator for approval before posting. Prevents the highest-impact mispronunciation scenario.

### Dictionary Growth

After each run, pipeline compares proper nouns from clusters against dictionary. Unrecognized names flagged for human addition. Prevents "first-time mispronunciation" problem.

## 3.3 Word-Level Timestamps

### ElevenLabs Returns

Character-level timing data. Pipeline transforms to word-level:

```json
{
  "slot": "LEAD",
  "words": [
    {"word": "Iran", "start": 0.0, "end": 0.35},
    {"word": "shot", "start": 0.38, "end": 0.62},
    {"word": "down", "start": 0.65, "end": 0.89}
  ],
  "sentences": [
    {
      "text": "Iran shot down a U.S. Army Apache near the Strait of Hormuz.",
      "start": 0.0,
      "end": 4.12,
      "trigger_gfx": "headline_reveal"
    }
  ],
  "duration_seconds": 38.7
}
```

### How Timestamps Drive Visuals

| Visual Event | Timing Source |
|-------------|-------------|
| Headline text reveal | First word of slot starts -> headline animates in |
| Lower-third appearance | 0.5s after slot audio begins (fixed offset from slot start) |
| SCAN card hard-cut | Start time of "One.", "Two.", "Three.", "Four." — keyword match in word array |
| Key stat emphasis | Words matching numbers/key phrases get text-scale pulse, timed to exact word |
| WHY IT MATTERS transition | Start time of WHY slot audio, minus 0.3s for visual transition lead-in |
| CIF tag flash | Appears when source sentence begins, holds for sentence duration |

**Critical insight:** Word-level timestamps are the bridge between Python orchestrator and Remotion renderer. Python builds the timing map. Remotion consumes it as props. The JSON spec is the contract.

## 3.4 Audio Post-Processing

Before passing to Remotion, lightweight processing via FFmpeg subprocess:

1. **Loudness normalization** — target -16 LUFS (YouTube/Facebook standard) via `ffmpeg -af loudnorm`
2. **Noise gate** — remove low-level artifacts (usually clean from ElevenLabs, catches edge cases)
3. **Head/tail trim** — trim silence padding for precise slot concatenation timing
4. **No compression, no EQ** — keep the cloned voice natural

## 3.5 Failure Handling

| Failure | Response |
|---------|----------|
| ElevenLabs API down | Retry 3x with exponential backoff (5s, 15s, 45s). If still down, abort run, log, alert. |
| One slot fails, others succeed | Retry that slot only. 3 failures -> abort full run. |
| Pronunciation glitch post-render | Flag in run log. Human adds to dictionary. Next day is clean. |
| Audio duration exceeds 2:15 | Log warning. Drop fourth SCAN item as overflow buffer. |
| Timestamps missing | Fall back to estimated timing (word count / 150 wpm). Less precise but functional. |

## ElevenLabs Plan Requirement

At ~2 min audio/day = ~60 min/month. **Creator plan ($22/mo, 2 hours)** is minimum. Pro plan ($99/mo, 4 hours) recommended for re-render headroom.
