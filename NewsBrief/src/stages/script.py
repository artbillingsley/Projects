# src/stages/script.py
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List

import structlog

from src.stages.extract import ExtractResult

log = structlog.get_logger()

MODEL = "claude-opus-4-6"

_REQUIRED_KEYS = {
    "lead_cluster_id",
    "scan_cluster_ids",
    "selection_rationale",
    "hook",
    "lead",
    "scan_intro",
    "scan_items",
    "why",
    "close",
}


class ScriptError(Exception):
    pass


@dataclass
class ScriptResult:
    lead_cluster_id: str
    scan_cluster_ids: List[str]
    selection_rationale: str
    hook: str
    lead: str
    scan_intro: str
    scan_items: List[str]
    why: str
    close: str
    platform_meta: Dict[str, Any]
    input_tokens: int
    output_tokens: int
    image_queries: Dict[str, str] = field(default_factory=dict)

    @property
    def full_scan(self) -> str:
        """Combines scan_intro and scan_items into a single string."""
        parts = [self.scan_intro] + self.scan_items
        return " ".join(parts)

    @property
    def word_count(self) -> int:
        """Total word count across all narration slots."""
        all_text = " ".join([
            self.hook,
            self.lead,
            self.full_scan,
            self.why,
            self.close,
        ])
        return len(all_text.split())


def _build_prompt(extract: ExtractResult) -> str:
    date_str = extract.brief_date.strftime("%B %-d, %Y")
    date_url = extract.brief_date.strftime("%Y-%m-%d")

    cluster_lines = []
    for c in extract.clusters:
        sources_str = ", ".join(c.sources) if c.sources else "N/A"
        what_changed_str = c.what_changed if c.what_changed else "N/A"
        cluster_lines.append(
            f"  ID: {c.id} | CIF_CODE: {c.cif_code} | POSITION: {c.position} | STATUS: {c.status} | CONFIDENCE: {c.confidence}\n"
            f"  HEADLINE: {c.headline}\n"
            f"  BODY: {c.body}\n"
            f"  WHY IT MATTERS: {c.why_this_matters}\n"
            f"  WHAT CHANGED: {what_changed_str}\n"
            f"  SOURCES: {sources_str}"
        )
    clusters_text = "\n\n".join(cluster_lines)

    return f"""You are a broadcast news writer for COGNOSCERE Daily Brief. Today is {date_str}. Issue: {extract.issue_number}.

You will receive a set of news clusters and must produce a structured 5-slot narration script for a 90-second video brief.

## INPUT CLUSTERS

{clusters_text}

## SLOT STRUCTURE

HARD LIMIT: 200 words total. Target is a 1:30 video. Every word must earn its place. Shorter and accurate is more impactful than longer and boring. Leave the audience wanting more — they come back tomorrow.

Write exactly these 5 slots:

1. HOOK (~12 words, ~5 sec): One punchy sentence. Use the lead story. No greetings.
2. LEAD (~60 words, ~25 sec): The featured story. Key facts only — who, what, why it matters. No background the audience already knows. Use CANONICAL numerals ("$70 billion", not "seventy billion").
3. SCAN (~90 words total, 3-4 items at 10-15 sec each): Start with scan_intro (e.g., "Three more, fast."). Each scan_item is 1-2 tight sentences. Self-contained — a listener must understand each item alone. Number: "One.", "Two.", "Three.", "Four." Use CANONICAL numerals.
4. WHY (~25 words, ~10 sec): One sentence connecting today's stories to the bigger picture. Make it land.
5. CLOSE (~12 words, ~5 sec): Date, call to action, done.

## SELECTION RULES

- Choose ONE lead story: prefer DEVELOPING status, then highest-stakes NEW story.
- Choose 3-4 SCAN stories: prefer NEW status, span different domains (politics, economy, tech, foreign policy, etc.). Do NOT repeat the lead story.
- Write a brief selection_rationale explaining your choices.

## NUMERIC STYLE

Always use CANONICAL numerals: "$70 billion", "$4.16", "850 billion", not spelled-out words for numbers.

## CTA LINKS (embed in close/platform_meta as appropriate)

- Full record: https://www.cognoscerellc.com/news/{date_url}/
- Subscribe: https://cognoscerellc.substack.com
- CIFaaS: https://cifaas.cognoscerellc.com

## PLATFORM META

Also generate platform_meta with these keys:
- youtube_title: short title for YouTube video
- youtube_description: 2-3 sentence description with CTA links
- youtube_tags: list of 5-10 relevant tags
- youtube_short_title: under 60 characters
- facebook_caption: 1-2 sentences with hook + link
- facebook_reel_caption: ultra-short (under 100 chars)
- instagram_caption: 2-3 sentences with hashtags
- linkedin_caption: professional framing, 2-3 sentences

## IMAGE QUERIES

For each slot, also provide a 2-3 word image search query for a stock photo that visually represents the story. These will be used to download background images from Unsplash for the Ken Burns effect in the video.

## OUTPUT FORMAT

Return ONLY valid JSON with this exact structure (no markdown fences, no extra text):

{{
  "lead_cluster_id": "<string (UUID)>",
  "scan_cluster_ids": ["<string (UUID)>", ...],
  "selection_rationale": "<string>",
  "hook": "<string>",
  "lead": "<string>",
  "scan_intro": "<string>",
  "scan_items": ["<string>", ...],
  "why": "<string>",
  "close": "<string>",
  "image_queries": {{"HOOK": "<2-3 word query>", "LEAD": "<2-3 word query>", "SCAN": "<2-3 word query>", "WHY": "<2-3 word query>", "CLOSE": "<2-3 word query>"}},
  "platform_meta": {{
    "youtube_title": "<string>",
    "youtube_description": "<string>",
    "youtube_tags": ["<string>", ...],
    "youtube_short_title": "<string>",
    "facebook_caption": "<string>",
    "facebook_reel_caption": "<string>",
    "instagram_caption": "<string>",
    "linkedin_caption": "<string>"
  }}
}}

FINAL REMINDER — WORD COUNT: The combined narration (hook + lead + scan_intro + all scan_items + why + close) MUST total under 200 words. Target 190. If your draft exceeds 200 words, cut ruthlessly before returning. Every extra word costs airtime. A 300-word script produces a 2-minute video that loses the audience. Aim for 190 words."""


def generate_script(extract: ExtractResult, client: Any) -> ScriptResult:
    log.info(
        "script.start",
        brief_id=extract.brief_id,
        issue=extract.issue_number,
        cluster_count=len(extract.clusters),
    )

    prompt = _build_prompt(extract)

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text.strip()

    # Strip markdown fences if present (Opus sometimes wraps JSON)
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw_text = "\n".join(lines).strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        log.error("script.json_parse_failed", raw_text=raw_text[:500])
        raise ScriptError(f"Failed to parse LLM response as JSON: {exc}") from exc

    missing = _REQUIRED_KEYS - data.keys()
    if missing:
        raise ScriptError(f"LLM response missing required keys: {sorted(missing)}")

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    result = ScriptResult(
        lead_cluster_id=data["lead_cluster_id"],
        scan_cluster_ids=data["scan_cluster_ids"],
        selection_rationale=data["selection_rationale"],
        hook=data["hook"],
        lead=data["lead"],
        scan_intro=data["scan_intro"],
        scan_items=data["scan_items"],
        why=data["why"],
        close=data["close"],
        platform_meta=data["platform_meta"],
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        image_queries=data.get("image_queries", {}),
    )

    # Enforce word count limit — target 200 words / 90 seconds
    MAX_WORDS = 250
    if result.word_count > MAX_WORDS:
        log.warning(
            "script.over_limit",
            word_count=result.word_count,
            max_words=MAX_WORDS,
            brief_id=extract.brief_id,
        )
        # Truncate scan items to bring under limit
        while result.word_count > MAX_WORDS and len(result.scan_items) > 2:
            dropped = result.scan_items.pop()
            result.scan_cluster_ids.pop()
            log.info("script.truncated_scan", dropped_words=len(dropped.split()))
        if result.word_count > MAX_WORDS:
            log.warning("script.still_over_limit", word_count=result.word_count)

    # Always ensure scan_intro matches actual item count
    count = len(result.scan_items)
    count_word = {1: "One more", 2: "Two more", 3: "Three more", 4: "Four more"}
    expected_intro = f"{count_word.get(count, str(count) + ' more')}, fast."
    if result.scan_intro != expected_intro:
        log.info("script.scan_intro_corrected", was=result.scan_intro, now=expected_intro)
        result.scan_intro = expected_intro

    log.info(
        "script.done",
        brief_id=extract.brief_id,
        lead_cluster_id=result.lead_cluster_id,
        scan_count=len(result.scan_cluster_ids),
        word_count=result.word_count,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    return result
