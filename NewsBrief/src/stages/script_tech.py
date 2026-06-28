# src/stages/script_tech.py
"""Generate a 90-second TechBrief script from DRS articles using Claude Opus."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List

import structlog

from src.stages.extract_tech import TechExtractResult

log = structlog.get_logger()

MODEL = "claude-opus-4-6"


class ScriptError(Exception):
    pass


@dataclass
class TechScriptResult:
    hook: str
    lead: str
    scan_intro: str
    scan_items: List[str]
    why: str
    close: str
    lead_title: str
    scan_titles: List[str]
    lead_source: str
    scan_sources: List[str]
    platform_meta: Dict
    input_tokens: int = 0
    output_tokens: int = 0
    image_queries: Dict = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        all_text = " ".join([
            self.hook, self.lead, self.scan_intro,
            " ".join(self.scan_items), self.why, self.close,
        ])
        return len(all_text.split())


_REQUIRED_KEYS = {
    "hook", "lead", "scan_intro", "scan_items", "why", "close",
    "lead_title", "scan_titles", "lead_source", "scan_sources",
    "platform_meta",
}


def _build_prompt(extract: TechExtractResult) -> str:
    date_str = extract.brief_date.strftime("%B %-d, %Y")
    date_url = extract.brief_date.strftime("%Y-%m-%d")

    articles_text = ""
    for i, a in enumerate(extract.articles):
        tags_str = ", ".join(a.tags[:5]) if a.tags else ""
        articles_text += f"""
ARTICLE {i+1}:
  Title: {a.title}
  Domain: {a.domain} | Urgency: {a.urgency} | Relevance: {a.relevance_score}
  Source: {a.source_name}
  Summary: {a.summary}
  Tags: {tags_str}
"""

    return f"""You are a cybersecurity and AI technology analyst for the COGNOSCERE Tech Brief. Today is {date_str}. Issue: {extract.issue_number}.

You produce a 90-second video narration for technology leaders, CISOs, and AI practitioners.

## INPUT ARTICLES

{articles_text}

## SLOT STRUCTURE

HARD LIMIT: 180 words total. Target 170. Every word must earn its place. This produces a 90-second video.

Write exactly these 5 slots:

1. HOOK (~10 words, ~4 sec): Lead with urgency. What demands attention today? No greetings.
2. LEAD (~50 words, ~20 sec): The top ACT-priority story. What happened, what's the exposure, what to do. Use CANONICAL numerals ("CVSS 10.0", "$12 billion").
3. SCAN (~70 words total, 2-3 items at 10-12 sec each): Start with scan_intro (e.g., "Two more to track."). Each item is 1-2 tight sentences. Number: "One.", "Two.", "Three." Prioritize ACT and PREPARE items.
4. WHY (~20 words, ~8 sec): Connect the dots. One sentence. Make it land.
5. CLOSE (~10 words, ~4 sec): Date, call to action, done.

## EDITORIAL VOICE

- You are a trusted security advisor, not a news anchor
- ACT items = "patch now" / "review immediately" urgency
- PREPARE items = "plan for this" / "assess your exposure"
- No hype, no speculation — facts and action

## OUTPUT FORMAT

Return ONLY valid JSON (no markdown fences):

{{
  "hook": "<string>",
  "lead": "<string>",
  "scan_intro": "<string>",
  "scan_items": ["<string>", ...],
  "why": "<string>",
  "close": "<string>",
  "lead_title": "<headline of lead story>",
  "scan_titles": ["<headline>", ...],
  "lead_source": "<source name>",
  "scan_sources": ["<source name>", ...],
  "platform_meta": {{
    "youtube_short_title": "<string under 100 chars> #Shorts",
    "facebook_caption": "<string>",
    "linkedin_caption": "<string>"
  }},
  "image_queries": {{"HOOK": "<2-3 words>", "LEAD": "<2-3 words>", "SCAN": "<2-3 words>", "WHY": "<2-3 words>"}}
}}

FINAL REMINDER — WORD COUNT: hook + lead + scan_intro + scan_items + why + close MUST total under 180 words. Aim for 170. A 240-word script produces a 2-minute video — too long."""


def generate_tech_script(extract: TechExtractResult, client: Any) -> TechScriptResult:
    log.info("script_tech.start", article_count=len(extract.articles), issue=extract.issue_number)

    prompt = _build_prompt(extract)

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text.strip()

    # Strip markdown fences if present
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw_text = "\n".join(lines).strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        log.error("script_tech.json_parse_failed", raw_text=raw_text[:500])
        raise ScriptError(f"Failed to parse LLM response as JSON: {exc}") from exc

    missing = _REQUIRED_KEYS - data.keys()
    if missing:
        raise ScriptError(f"LLM response missing required keys: {sorted(missing)}")

    result = TechScriptResult(
        hook=data["hook"],
        lead=data["lead"],
        scan_intro=data["scan_intro"],
        scan_items=data["scan_items"],
        why=data["why"],
        close=data["close"],
        lead_title=data["lead_title"],
        scan_titles=data["scan_titles"],
        lead_source=data["lead_source"],
        scan_sources=data["scan_sources"],
        platform_meta=data["platform_meta"],
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        image_queries=data.get("image_queries", {}),
    )

    # Enforce word count limit
    MAX_WORDS = 250
    if result.word_count > MAX_WORDS:
        log.warning("script_tech.over_limit", word_count=result.word_count, max_words=MAX_WORDS)
        while result.word_count > MAX_WORDS and len(result.scan_items) > 1:
            result.scan_items.pop()
            result.scan_titles.pop()
            result.scan_sources.pop()
            log.info("script_tech.truncated_scan")

    # Ensure scan_intro matches item count
    count = len(result.scan_items)
    count_word = {1: "One more", 2: "Two more", 3: "Three more", 4: "Four more"}
    expected_intro = f"{count_word.get(count, str(count) + ' more')} to track."
    if result.scan_intro != expected_intro:
        log.info("script_tech.scan_intro_corrected", was=result.scan_intro, now=expected_intro)
        result.scan_intro = expected_intro

    log.info(
        "script_tech.done",
        word_count=result.word_count,
        scan_count=len(result.scan_items),
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )

    return result
