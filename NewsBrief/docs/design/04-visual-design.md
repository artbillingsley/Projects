# Section 4: Remotion Visual Design & Template System

## Governing Principle

The visuals must do three things simultaneously: signal intelligence-grade credibility, sync precisely to the voice track, and remain legible at mobile resolution on a 3-inch screen. Every design decision serves at least two of those three.

## 4.1 Remotion Project Structure

```
newsbrief-renderer/
+-- package.json
+-- remotion.config.ts
+-- src/
|   +-- Root.tsx                    # Entry point — registers all compositions
|   +-- compositions/
|   |   +-- AnchorBrief.tsx         # Full 2-min anchor (sequences all slots)
|   |   +-- MicroClip.tsx           # Generic micro-clip wrapper (slot + CLOSE)
|   |   +-- Thumbnail.tsx           # Single-frame YouTube thumbnail
|   +-- slots/
|   |   +-- Hook.tsx
|   |   +-- Lead.tsx
|   |   +-- Scan.tsx                # Contains ScanItem sub-component
|   |   +-- WhyItMatters.tsx
|   |   +-- Close.tsx
|   +-- components/
|   |   +-- AnimatedHeadline.tsx    # Character-by-character headline reveal
|   |   +-- LowerThird.tsx          # Headline + CIF tag + confidence + sources
|   |   +-- CifTag.tsx              # [CIF-XXXX] badge
|   |   +-- ConfidenceTag.tsx       # Confidence: High / Medium badge
|   |   +-- ScanCard.tsx            # Numbered card for SCAN items
|   |   +-- SourceBar.tsx           # Source logos / attribution line
|   |   +-- ProgressBar.tsx         # Thin top-of-frame progress indicator
|   |   +-- Wordmark.tsx            # COGNOSCERE lockup
|   +-- design/
|   |   +-- theme.ts                # Colors, fonts, spacing, easing curves
|   |   +-- fonts.ts                # Font loading
|   |   +-- animations.ts           # Shared spring/easing presets
|   +-- types/
|       +-- spec.ts                 # TypeScript types matching Python JSON spec
+-- public/
|   +-- fonts/
|   +-- assets/                     # Logo, map templates, motifs
+-- render.sh                       # CLI wrapper called by Python subprocess
```

### Python Calls Remotion Via

```bash
npx remotion render src/Root.tsx AnchorBrief \
  --props="./tmp/2026-06-10/remotion-spec.json" \
  --output="./tmp/2026-06-10/anchor-16x9.mp4" \
  --width=1920 --height=1080 --fps=30
```

The `--props` flag is the entire bridge. Python writes the JSON. Remotion reads it. No other coupling.

## 4.2 Visual Design System

### Color Palette

| Role | Hex | Usage |
|------|-----|-------|
| Background | #0F1419 | Near-black with warm undertone. Dark backgrounds maximize text contrast. |
| Surface | #1A2332 | Cards, lower thirds, content panels. Slightly elevated from background. |
| Primary text | #F5F0E8 | Warm white matching CDB's cream palette. |
| Secondary text | #9BA8B7 | Timestamps, source attributions, supporting info. |
| Gold accent | #C9A227 | Headlines, story numbers, key emphasis. Brand anchor color on screen. |
| Developing tag | #D4855A | Amber/terracotta for DEVELOPING stories. |
| New tag | #4A9B8E | Teal for NEW stories. Matches CDB tag color. |
| Confidence tag | #6B7D5E | Muted olive. Present but not competing. |
| Red accent | #C75050 | Reserved for breaking/critical. Used sparingly. |
| Progress bar | #C9A227 at 40% opacity | Thin line at top showing elapsed time. |

### Typography

| Role | Font | Weight | Size (1080p) | Rationale |
|------|------|--------|-------------|-----------|
| Headlines | DM Serif Display | Regular | 64-72px | Serif signals editorial authority. High video legibility. |
| Body / VO text | Inter | Regular/Medium | 36-42px | Matches CDB body font. Clean, high x-height. |
| Data / tags | JetBrains Mono | Regular | 28-32px | Monospace for CIF tags, numbers. Signals structured data. |
| Wordmark | Franklin Gothic Medium | -- | Per brand spec | COGNOSCERE lockup, CLOSE only. |

### Animation Presets

```typescript
// Shared spring configs
export const SPRING_ENTER = { damping: 15, mass: 0.8, stiffness: 180 };  // Confident entrance
export const SPRING_EXIT  = { damping: 20, mass: 0.6, stiffness: 200 };  // Crisp exit
export const SPRING_SUBTLE = { damping: 20, mass: 1.0, stiffness: 120 }; // Gentle float-in

// Timing helpers
export const HEADLINE_REVEAL_SPEED = 2;    // frames per character
export const CARD_TRANSITION_FRAMES = 8;   // ~0.27s at 30fps
export const LOWER_THIRD_DELAY = 15;       // frames after slot start
```

Springs over linear easing everywhere. Springs look intentional. Linear looks robotic. This is the single biggest visual quality differentiator.

## 4.3 Per-Slot Visual Treatment

### HOOK (0:00-0:10)

- **No logo. No branding.** Just the statement. Brand earns attention by leading with value.
- Text: character-by-character reveal, gold, DM Serif Display 72px, timed to voice
- Background: #0F1419 with subtle radial gradient or low-opacity map texture (atmospheric, not literal)
- CIF tag + DEVELOPING badge fade in bottom-right, small
- Transition to LEAD: quick dissolve (6 frames)

### LEAD (0:10-0:50)

- **Lower third** enters with spring animation: headline (gold, DM Serif Display), CIF tag + confidence (JetBrains Mono, muted)
- **Sentence display panel:** sentences appear one at a time. Current = full brightness (#F5F0E8). Previous dims to secondary text. "Reading along" effect.
- **Key fact emphasis:** numbers/critical phrases scale up 5% with gold flash, timed to word timestamps
- Source bar at bottom: outlet names in secondary text, persistent
- Transition to SCAN: lower third slides out, panel clears with 0.2s wipe

### SCAN (0:50-1:30)

- **Hard cuts between items.** No dissolves. Card snaps in when voice says "One."
- Large gold number (JetBrains Mono, 96px), story text centered (Inter Medium, 40px), CIF tag bottom
- Background color shifts subtly per card: #0F1419 -> #141E2B (alternating)
- SCAN items detected in word-timing by matching "One.", "Two.", "Three.", "Four."
- Number is the scroll-stopper for standalone micro-clips

### WHY IT MATTERS (1:30-1:50)

- **Visual reset.** Background shifts to #1A2332 (surface color)
- "WHY IT MATTERS" header: gold, small caps, JetBrains Mono
- Text: sentence-by-sentence, centered, larger (Inter Medium, 48px). Editorial voice gets room.
- **Through-line motif:** horizontal connecting line linking 2-3 concept nodes. Spring-animated, gold line.
- No CIF tags. No sources. This is synthesis, not reporting.

### CLOSE (1:50-2:00)

- COGNOSCERE wordmark (Franklin Gothic Medium) fades in center. First and only time full logo appears.
- CIFaaS URL + "Read the full record" below. Understated CTA.
- **"Decide."** appears last. Alone. Gold. Holds 1.5 seconds. Brand signature.
- Reused verbatim as outro on every micro-clip.

## 4.4 Responsive Layout (16:9 vs 9:16)

One composition, two render targets. Components adapt based on aspect ratio:

| Element | 16:9 (1920x1080) | 9:16 (1080x1920) |
|---------|------------------|------------------|
| HOOK text | Centered, 72px | Centered, 64px, more line breaks |
| LEAD headline | Top-left lower third | Top-center, full width |
| LEAD body panel | Center-right, 60% width | Center, 90% width |
| SCAN number | Left-aligned, text right | Top-center, text below |
| WHY through-line | Horizontal, bottom third | Vertical, right edge |
| CLOSE lockup | Centered | Centered, tighter spacing |
| Source bar | Bottom-left | Bottom-center |
| Progress bar | Top, full width | Top, full width |

## 4.5 Render Matrix

| Output | Composition | Aspect | Source Slots |
|--------|------------|--------|-------------|
| anchor-16x9.mp4 | AnchorBrief | 16:9 | All 5 in order |
| anchor-9x16.mp4 | AnchorBrief | 9:16 | All 5 in order |
| clip-C1-*.mp4 | MicroClip | 9:16 | HOOK + LEAD (compressed) + WHY tail + CLOSE |
| clip-C2-*.mp4 | MicroClip | 9:16 | SCAN item 2 + CLOSE |
| clip-C3-*.mp4 | MicroClip | 9:16 | SCAN item 3 + CLOSE |
| clip-C4-*.mp4 | MicroClip | 9:16 | SCAN item 4 + CLOSE |
| clip-T0-*.mp4 | MicroClip | 9:16 | "Today in One Breath" teaser + CLOSE |
| thumbnail.png | Thumbnail | 16:9 | HOOK text, single frame |

**8 renders per daily run.** Render time TBD pending R3 benchmark on target EC2 instance.

## 4.6 Caption Generation (R9)

Word-level timestamps already exist as the master clock. The pipeline emits SRT/VTT subtitle files as a render byproduct at near-zero cost.

**Per-platform handling:**
- **YouTube:** Upload `.srt` via captions API alongside video. Platform handles display.
- **Facebook:** Upload `.srt` as captions track. Platform handles display.
- **Instagram Reels:** No separate caption track support. Burn captions into the video during Remotion render as a styled text overlay (bottom-center, Inter Medium 32px, white on semi-transparent dark background). Instagram-targeted renders include burned-in captions; YouTube/Facebook/LinkedIn renders do not (those use platform-native caption tracks).
- **LinkedIn:** Upload `.srt` alongside video.

**Caption generation logic (Python, ~20 lines):**
```python
def generate_srt(word_timings: list[dict], max_chars_per_line=42) -> str:
    # Group words into subtitle segments (2-3 seconds each)
    # Emit SRT format with sequential numbering
    # Timing from word-level timestamps ensures sync with audio
```

## 4.7 JSON Spec Contract

Python produces the spec. Remotion consumes it. Full schema documented in the worked example in the design conversation. Key structure:

```json
{
  "brief_id": "N103",
  "date": "2026-06-10",
  "slots": [
    {
      "type": "HOOK",
      "copy": "...",
      "audio_file": "./tmp/2026-06-10/audio/hook.mp3",
      "words": [{"word": "An", "start": 0.0, "end": 0.15}],
      "duration_seconds": 9.8,
      "gfx": {"cif_tag": "CIF-DX9F", "status": "DEVELOPING"},
      "extractable": false
    }
  ],
  "clips": [
    {
      "id": "C1",
      "title": "Hormuz: U.S. and Iran Trade Strikes",
      "slots": ["HOOK", "LEAD_COMPRESSED", "WHY_TAIL"],
      "platform_meta": {
        "youtube_shorts_title": "...",
        "instagram_caption": "...",
        "hashtags": ["#Iran", "#Hormuz", "#COGNOSCERE"]
      }
    }
  ],
  "render_targets": ["anchor-16x9", "anchor-9x16", "C1", "C2", "C3", "C4", "T0", "thumbnail"]
}
```

**The spec is the single source of truth.** If a render fails, the spec is all you need to re-run. If you want to manually adjust a headline, edit the spec and re-render.
