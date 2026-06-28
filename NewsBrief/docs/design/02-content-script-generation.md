# Section 2: Content Selection & Script Generation

## Anchor Script Template v0.1

**Source of record:** The day's CDB (e.g. Issue #N103, June 10 2026)
**Voice:** ElevenLabs clone. House style: short declaratives, no hedging, no em dashes, punchline first.
**Read pace target:** ~150 words/min measured authoritative. **2:00 = 290-310 words.** Treat 2:00 as a ceiling, not a quota.

## Slot Structure

Five typed slots. Each slot is **self-contained** — no line refers to another slot — which is the rule that makes atomization mechanical. The anchor script is the slots played in order. Every micro-clip is one slot (or one slot plus a one-line tag) lifted out whole. Write once, emit both.

| Slot | Timecode | Word Budget | Job |
|------|----------|-------------|-----|
| HOOK | 0:00-0:10 | ~25 | Stop the scroll. Biggest stakes, stated as consequence, not headline. |
| LEAD | 0:10-0:50 | ~100 | Top story, full CIF treatment: what happened -> what changed -> key facts. |
| SCAN | 0:50-1:30 | ~100 | 3-4 items, ~25 words each. Fast cadence. One pattern interrupt per item. |
| WHY IT MATTERS | 1:30-1:50 | ~50 | The thread. Tie the day together for the viewer. This is the moat. |
| CLOSE | 1:50-2:00 | ~20 | Provenance stamp + soft CTA + single-word sign-off. |

## The Template (Reusable Skeleton)

```
[HOOK] 0:00-0:10 ~ 25w
VO: {single hardest consequence of the day, personal stakes if possible}
GFX: full-bleed cold open, no logo yet. Story art or map. CIF tag bottom-right.
EXTRACT -> none (hook recombines with LEAD for Clip 1)

[LEAD] 0:10-0:50 ~ 100w
VO: {what happened}. {what changed}. {2-3 load-bearing facts}. {one-line stakes}.
GFX: lower-third headline + [CIF-XXXX] + confidence tag. Source logos as cited.
EXTRACT -> Clip 1 (HOOK + compressed LEAD + one why-tag)

[SCAN] 0:50-1:30 ~ 100w
VO: "{N} more, fast."
  One. {item, ~25w, self-contained}.
  Two. {item}.
  Three. {item}.
  Four. {item}.
GFX: numbered cards, hard cut per item. [CIF-XXXX] tag flashes per item.
EXTRACT -> Clips 2..N (each numbered item is one standalone clip)

[WHY IT MATTERS] 1:30-1:50 ~ 50w
VO: "Here is the thread." {synthesis connecting LEAD + SCAN to the viewer}.
GFX: connecting lines / through-line motif in CDB palette. No new facts on screen.
EXTRACT -> tail tag for Clip 1, or standalone "thread of the day" clip

[CLOSE] 1:50-2:00 ~ 20w
VO: "That is the brief for {date}. {provenance line}. {CTA}." {SIGN-OFF}.
GFX: COGNOSCERE lockup, CIFaaS URL, "Read the full record" + sign-off card.
EXTRACT -> standard outro, appended to every micro-clip
```

## Story Selection Logic

The LLM (`claude-sonnet-4-20250514`) receives all clusters from the database and selects based on:

1. **Developing stories first** — stories tagged DEVELOPING get priority (active, breaking relevance)
2. **Impact breadth** — stories with widest "Why This Matters" relevance to general audience
3. **Narrative variety** — avoid three stories from same domain (e.g., not three Iran stories)
4. **Recency weight** — NEW stories over carried-forward stories

The LLM returns structured JSON: which stories are lead, secondary, and rapid-scan, plus editorial rationale logged for audit.

## Self-Containment Rule (Critical)

**Each SCAN item must be comprehensible if read in isolation with zero context from HOOK or LEAD.** If it requires setup, rewrite it to embed the setup. This rule is enforced in the LLM prompt and is the architectural constraint that makes micro-clip extraction mechanical.

## Worked Example — Issue #N103, June 10 2026

**[HOOK] 0:00-0:10**
An American helicopter is down near the Strait of Hormuz. Iran and the United States are trading fire again. And the war is already at your pump.

**[LEAD] 0:10-0:50**
Iran shot down a U.S. Army Apache near the Strait of Hormuz. The most serious direct exchange since the ceasefire two months ago. Central Command answered with strikes on Iranian air defense and radar. Both crew were rescued within two hours. They are stable. Then Iran's Revolutionary Guards hit back. Missiles and drones at U.S. bases in Bahrain, Jordan, and Kuwait. Most were intercepted. No personnel harmed. But the Strait of Hormuz carries one fifth of the world's oil. And it is now a shooting gallery. Oil climbed. The ceasefire is not broken. The confidence in it is.

**[SCAN] 0:50-1:30**
Four more, fast.
One. The House sent Trump a seventy billion dollar immigration bill. It funds ICE and Border Patrol through 2029. No new oversight.
Two. Trump put a housing regulator atop the intelligence community. Section 702, the surveillance law, can lapse this week. During a war.
Three. Gas sits at four-sixteen a gallon. A dollar above last year. The President calls it "not very high."
Four. OpenAI filed to go public above eight hundred fifty billion dollars. After Anthropic. After SpaceX. The AI giants are heading for the exits.

**[WHY IT MATTERS] 1:30-1:50**
Here is the thread. The war near Hormuz is the same war showing up in your gas tank. It is escalating while the people who watch foreign threats are in turmoil, and the law that lets them watch may expire this week. One crisis abroad. The bill arriving at home.

**[CLOSE] 1:50-2:00**
That is the brief for June tenth. Every source shown. Every claim tagged. The full record is linked below. Decide.

**Running length:** ~305 words = ~2:02. Trim LEAD interception detail if needed.

## Micro-Clips (Derived from Slots)

| Clip | Source Slot(s) | Length | Description |
|------|---------------|--------|-------------|
| C1 - Hormuz | HOOK + LEAD (compressed) + WHY tail | 35-40s | Flagship discovery clip |
| C2 - Section 702 | SCAN item 2 | 20-25s | Security/policy audience |
| C3 - Gas $4.16 | SCAN item 3 | 20-25s | Highest mass-relatability |
| C4 - AI IPO trio | SCAN item 4 | 20-25s | LinkedIn + tech reach |
| T0 - One Breath | "Today in One Breath" verbatim from CDB | ~15s | Teaser/trailer |

## Production Notes

### Sign-off
**"Decide."** — ties to CIFaaS "tracked, attributable decisions" and advisory line. One word, instantly ownable.

### Number Formatting (Amended per R2)
**Two-step process:** The LLM emits canonical numeric values (`$4.16`, `$70 billion`, `214-212`). A deterministic Python formatter (`format_for_speech()`) converts to spoken forms ("four sixteen", "seventy billion", "two fourteen to two twelve") before passing to ElevenLabs. This eliminates numeric drift — the LLM never invents spoken numbers, and every canonical value can be verified against the source `clusters` data.

### Slot -> JSON
Each segment emitted as a typed object so one CDB generates anchor script and all micro-clips:

```json
{
  "type": "LEAD",
  "timecode_target": "0:10-0:50",
  "word_budget": 100,
  "copy": "...",
  "gfx": "...",
  "source_tags": ["CIF-DX9F"],
  "extractable": true,
  "clip_id": "C1"
}
```

The anchor render concatenates slots in order. The clip render filters `extractable == true` and wraps each with the standard CLOSE. Same source, two output classes, zero double-writing.
