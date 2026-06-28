# src/stages/spec.py
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

import requests
import structlog

from src.stages.audio import AudioResult
from src.stages.extract import ClusterData, ExtractResult
from src.stages.script import ScriptResult

log = structlog.get_logger()

# Slot name -> audio filename stem
_SLOT_FILE: Dict[str, str] = {
    "HOOK": "hook",
    "LEAD": "lead",
    "SCAN": "scan",
    "WHY": "why",
    "CLOSE": "close",
}


def _cluster_by_id(clusters: List[ClusterData], cluster_id: str) -> Optional[ClusterData]:
    """Return the cluster with the given id, or None if not found."""
    for c in clusters:
        if c.id == cluster_id:
            return c
    return None


NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "a860ab09-4573-4c27-b6b4-62de1630dcb6")
NEWSAPI_URL = "https://eventregistry.org/api/v1/article/getArticles"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


# ---------------------------------------------------------------------------
# Image sourcing: og:image from cluster_sources (primary) -> NewsAPI (fallback)
# ---------------------------------------------------------------------------

_PREFERRED_OUTLETS = ["reuters", "ap", "bbc", "nyt", "wsj", "wapo", "bloomberg",
                      "aljazeera", "guardian", "ft", "latimes", "npr", "rferl",
                      "nbcnews", "cnn", "politico", "axios"]
_SKIP_DOMAINS = ["youtube.com", "youtu.be", "twitter.com", "x.com", "facebook.com"]


def _scrape_og_image(url: str) -> Optional[str]:
    """Fetch a URL and extract the og:image meta tag."""
    from html.parser import HTMLParser

    class _OGParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.og_image: Optional[str] = None
        def handle_starttag(self, tag, attrs):
            if tag == "meta":
                d = dict(attrs)
                if d.get("property") == "og:image" or d.get("name") == "og:image":
                    val = d.get("content", "")
                    if val and val.startswith("http"):
                        self.og_image = val

    try:
        resp = requests.get(
            url, timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (compatible; CognoscereBot/1.0)"},
            allow_redirects=True,
        )
        if resp.status_code != 200:
            return None
        parser = _OGParser()
        parser.feed(resp.text[:60000])  # Only parse first 60KB
        return parser.og_image
    except Exception:
        return None


def _fetch_image_from_sources(cluster_sources: list) -> Optional[str]:
    """Try to scrape og:image from the cluster's actual source article URLs.

    Prioritizes major news outlets and skips social media / video sites.
    Returns the first valid og:image URL found, or None.
    """
    # Sort sources: preferred outlets first
    def _outlet_priority(source_url: str) -> int:
        url_lower = source_url.lower()
        for i, outlet in enumerate(_PREFERRED_OUTLETS):
            if outlet in url_lower:
                return i
        return 100

    # Filter out social media and video sites
    valid_urls = [
        url for url in cluster_sources
        if not any(skip in url.lower() for skip in _SKIP_DOMAINS)
    ]
    # Sort by outlet priority
    valid_urls.sort(key=_outlet_priority)

    for url in valid_urls[:8]:  # Try up to 8 URLs
        og_image = _scrape_og_image(url)
        if og_image:
            # Validate it's not a logo/icon
            if any(skip in og_image.lower() for skip in ["logo", "icon", "favicon", "sprite", "1x1"]):
                continue
            log.info("spec.image.og_found", url=url[:60], image=og_image[:80])
            return og_image

    return None

def _generate_image_queries(
    extract_result: ExtractResult,
    script_result: ScriptResult,
    anthropic_api_key: str,
) -> Dict[str, Dict[str, str]]:
    """Ask Claude to generate precise image search queries + fallback data for each story.

    Returns a dict mapping slot keys to dicts with "query", "icon", and "data_point".
    """
    import anthropic

    # Build the stories to search for
    stories: Dict[str, str] = {}
    lead_cluster: Optional[ClusterData] = None
    for c in extract_result.clusters:
        if c.id == script_result.lead_cluster_id:
            lead_cluster = c
            break

    if lead_cluster:
        stories["LEAD"] = f"Headline: {lead_cluster.headline}\nSummary: {lead_cluster.body[:200]}"

    for idx, cluster_id in enumerate(script_result.scan_cluster_ids):
        for c in extract_result.clusters:
            if c.id == cluster_id:
                stories[f"SCAN_{idx}"] = f"Headline: {c.headline}\nSummary: {c.body[:200]}"
                break

    if not stories:
        return {}

    stories_text = ""
    for key, desc in stories.items():
        stories_text += f"\n[{key}]\n{desc}\n"

    prompt = f"""You are a photo editor selecting images for a news video brief. For each story below, provide:
1. A precise 3-4 word search query that would find a NEWS PHOTO directly related to this specific story.
2. A single emoji icon representing the topic (for fallback graphics).
3. A key data point or short phrase (max 4 words) from the story for a fallback branded graphic.

Search query rules:
- The query should find photos OF the actual event, people, or location in the story
- Use proper nouns (names, places) when possible
- Avoid generic terms that could match unrelated stories
- For military/conflict stories: include the specific conflict/location
- For political stories: include the politician's name and the specific action
- For economic stories: include the specific metric or policy

Stories:
{stories_text}

Return ONLY valid JSON mapping slot keys to objects with "query", "icon", and "data_point":
{{"LEAD": {{"query": "Iran Apache helicopter Hormuz", "icon": "\\ud83d\\ude81", "data_point": "Strait of Hormuz"}}, "SCAN_0": {{"query": "immigration bill House vote", "icon": "\\ud83c\\udfe4", "data_point": "$70 Billion"}}, ...}}"""

    try:
        client = anthropic.Anthropic(api_key=anthropic_api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
        # Strip markdown code fences if present
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        data: Dict[str, Dict[str, str]] = json.loads(raw)

        # HOOK and WHY use the same image/data as LEAD
        if "LEAD" in data:
            data["HOOK"] = data["LEAD"].copy()
            data["WHY"] = data["LEAD"].copy()

        log.info("spec.image.queries_generated", queries={k: v.get("query", "") for k, v in data.items()})
        return data
    except Exception as e:
        log.warning("spec.image.query_generation_failed", error=str(e))
        return {}


def _validate_image_relevance(article_title: str, story_headline: str, anthropic_api_key: str) -> bool:
    """Ask Claude if the article's image is likely relevant to our story."""
    import anthropic

    try:
        client = anthropic.Anthropic(api_key=anthropic_api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=10,
            messages=[{"role": "user", "content": f"""Is this news article about the SAME story or closely related topic?

Our story: {story_headline}
Article found: {article_title}

Answer only YES or NO."""}],
        )
        answer = response.content[0].text.strip().upper()
        return answer.startswith("YES")
    except Exception:
        return False


def _fetch_news_image(query: str, story_headline: str, anthropic_api_key: str) -> Optional[str]:
    """Search NewsAPI.ai and validate relevance via LLM before returning."""
    try:
        resp = requests.post(
            NEWSAPI_URL,
            json={
                "action": "getArticles",
                "keyword": query,
                "articlesCount": 10,
                "articlesSortBy": "date",
                "articleBodyLen": 0,
                "resultType": "articles",
                "apiKey": NEWSAPI_KEY,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        articles = resp.json().get("articles", {}).get("results", [])

        for art in articles:
            image_url = art.get("image", "")
            if not image_url or not image_url.startswith("http"):
                continue
            if any(skip in image_url.lower() for skip in [
                "logo", "icon", "favicon", "placeholder", "default",
                "avatar", "sprite", "1x1", "pixel",
            ]):
                continue

            # Validate relevance: check if the article is about the same story
            article_title = art.get("title", "")
            if article_title and _validate_image_relevance(article_title, story_headline, anthropic_api_key):
                log.info("spec.image.validated", query=query, article=article_title[:60])
                return image_url
            else:
                log.info("spec.image.rejected", query=query, article=(article_title or "(no title)")[:60])

        return None
    except Exception as e:
        log.warning("newsapi.search.failed", query=query[:50], error=str(e))
    return None


def _download_image(image_url: str, filename: str, output_dir: str) -> Optional[str]:
    """Download an image URL to output_dir, return relative path or None."""
    try:
        resp = requests.get(image_url, timeout=15, allow_redirects=True,
                           headers={"User-Agent": "Mozilla/5.0 (compatible; CognoscereBot/1.0)"})
        content_type = resp.headers.get("content-type", "")
        if resp.status_code != 200 or len(resp.content) < 5000:
            return None
        if "image" not in content_type and not image_url.endswith((".jpg", ".jpeg", ".png", ".webp")):
            return None
        ext = "png" if "png" in content_type else "jpg"
        full_filename = f"{filename}.{ext}"
        path = os.path.join(output_dir, full_filename)
        with open(path, "wb") as f:
            f.write(resp.content)
        return f"images/{full_filename}"
    except Exception:
        return None


def _download_images(
    extract_result: ExtractResult,
    script_result: ScriptResult,
    output_dir: str,
    anthropic_api_key: str,
) -> Tuple[Dict[str, str], Dict[str, Dict[str, str]]]:
    """Download images for each story. Three-tier approach:

    1. Scrape og:image from the cluster's actual source article URLs (most relevant)
    2. LLM-validated NewsAPI.ai search (fallback)
    3. Branded fallback graphic (always available)

    Returns (image_paths, fallback_data).
    """
    os.makedirs(output_dir, exist_ok=True)
    image_paths: Dict[str, str] = {}
    fallback_data: Dict[str, Dict[str, str]] = {}

    # Generate fallback data (icons + data points) via LLM for all stories
    queries = _generate_image_queries(extract_result, script_result, anthropic_api_key)
    for slot_key, slot_data in queries.items():
        slot_type = slot_key.split("_")[0]
        if slot_type not in fallback_data:
            fallback_data[slot_type] = {
                "icon": slot_data.get("icon", ""),
                "data_point": slot_data.get("data_point", ""),
            }

    # Build cluster lookup
    clusters_by_id = {c.id: c for c in extract_result.clusters}

    # Map slots to cluster IDs
    slot_to_cluster: Dict[str, str] = {
        "HOOK": script_result.lead_cluster_id,
        "LEAD": script_result.lead_cluster_id,
        "WHY": script_result.lead_cluster_id,
    }
    for idx, cid in enumerate(script_result.scan_cluster_ids):
        slot_to_cluster[f"SCAN_{idx}"] = cid

    downloaded: Dict[str, str] = {}  # cluster_id -> rel_path (dedup)

    for slot_key in ["LEAD", "SCAN_0", "SCAN_1", "SCAN_2", "SCAN_3", "HOOK", "WHY"]:
        cluster_id = slot_to_cluster.get(slot_key, "")
        if not cluster_id:
            continue

        # Dedup
        if cluster_id in downloaded:
            image_paths[slot_key] = downloaded[cluster_id]
            continue

        cluster = clusters_by_id.get(cluster_id)
        if not cluster:
            continue

        filename = slot_key.lower().replace("_", "-")
        image_found = False

        # --- Tier 1: Scrape og:image from actual source article URLs ---
        if cluster.source_urls:
            og_image_url = _fetch_image_from_sources(cluster.source_urls)
            if og_image_url:
                rel_path = _download_image(og_image_url, filename, output_dir)
                if rel_path:
                    downloaded[cluster_id] = rel_path
                    image_paths[slot_key] = rel_path
                    log.info("spec.image.from_source", slot=slot_key, url=og_image_url[:80])
                    image_found = True

        # --- Tier 2: LLM-validated NewsAPI search ---
        if not image_found:
            query_data = queries.get(slot_key, {})
            query = query_data.get("query", "")
            if query:
                news_image_url = _fetch_news_image(query, cluster.headline, anthropic_api_key)
                if news_image_url:
                    rel_path = _download_image(news_image_url, filename, output_dir)
                    if rel_path:
                        downloaded[cluster_id] = rel_path
                        image_paths[slot_key] = rel_path
                        log.info("spec.image.from_newsapi", slot=slot_key, url=news_image_url[:80])
                        image_found = True

        if not image_found:
            log.info("spec.image.using_fallback", slot=slot_key, headline=cluster.headline[:50])

    return image_paths, fallback_data


def _build_slots(
    extract_result: ExtractResult,
    script_result: ScriptResult,
    audio_result: AudioResult,
    audio_dir: str,
    image_paths: Optional[Dict[str, str]] = None,
    fallback_data: Optional[Dict[str, Dict[str, str]]] = None,
) -> List[Dict[str, Any]]:
    """Assemble the 5 slot dicts from script + audio data."""
    _imgs = image_paths or {}
    _fallbacks = fallback_data or {}

    def _audio_path(filename: str) -> str:
        """Return a staticFile()-compatible path for Remotion's <Audio>.

        Audio files must be in the Remotion project's public/ directory.
        The render stage copies them there before invoking Remotion.
        The path is relative to public/ — e.g. "audio/hook.mp3".
        """
        return f"audio/{filename}"

    # Index audio slots by name for fast lookup
    audio_by_name: Dict[str, Any] = {s.slot_name: s for s in audio_result.slots}

    lead_cluster = _cluster_by_id(extract_result.clusters, script_result.lead_cluster_id)

    slots: List[Dict[str, Any]] = []

    # ---- HOOK ----------------------------------------------------------------
    hook_audio = audio_by_name.get("HOOK")
    hook_slot: Dict[str, Any] = {
        "type": "HOOK",
        "copy": script_result.hook,
        "audio_file": _audio_path("hook.mp3"),
        "words": hook_audio.word_timings if hook_audio else [],
        "duration_seconds": hook_audio.duration_seconds if hook_audio else 0.0,
        "gfx": {},
    }
    if _imgs.get("HOOK"):
        hook_slot["image_file"] = _imgs["HOOK"]
    if _fallbacks.get("HOOK"):
        hook_slot["fallback_icon"] = _fallbacks["HOOK"].get("icon", "")
        hook_slot["fallback_data_point"] = _fallbacks["HOOK"].get("data_point", "")
    slots.append(hook_slot)

    # ---- LEAD ----------------------------------------------------------------
    lead_audio = audio_by_name.get("LEAD")
    lead_gfx: Dict[str, Any] = {}
    if lead_cluster is not None:
        lead_gfx = {
            "cif_tag": f"CIF-{lead_cluster.cif_code}",
            "status": lead_cluster.status,
            "confidence": lead_cluster.confidence,
            "sources": lead_cluster.sources,
            "headline": lead_cluster.headline,
        }
    lead_slot: Dict[str, Any] = {
        "type": "LEAD",
        "copy": script_result.lead,
        "audio_file": _audio_path("lead.mp3"),
        "words": lead_audio.word_timings if lead_audio else [],
        "duration_seconds": lead_audio.duration_seconds if lead_audio else 0.0,
        "gfx": lead_gfx,
        "extractable": True,
        "clip_id": "C1",
    }
    if _imgs.get("LEAD"):
        lead_slot["image_file"] = _imgs["LEAD"]
    if _fallbacks.get("LEAD"):
        lead_slot["fallback_icon"] = _fallbacks["LEAD"].get("icon", "")
        lead_slot["fallback_data_point"] = _fallbacks["LEAD"].get("data_point", "")
    slots.append(lead_slot)

    # ---- SCAN ----------------------------------------------------------------
    scan_audio = audio_by_name.get("SCAN")
    scan_items_data: List[Dict[str, Any]] = []
    for idx, (item_text, cluster_id) in enumerate(
        zip(script_result.scan_items, script_result.scan_cluster_ids)
    ):
        cluster = _cluster_by_id(extract_result.clusters, cluster_id)
        item: Dict[str, Any] = {
            "copy": item_text,
            "cluster_id": cluster_id,
        }
        if cluster is not None:
            item["headline"] = cluster.headline
            item["status"] = cluster.status
        # Items at index > 0 are extractable short clips
        if idx > 0:
            item["extractable"] = True
            item["clip_id"] = f"C{idx + 2}"
        # Per-item image and fallback
        scan_key = f"SCAN_{idx}"
        if _imgs.get(scan_key):
            item["image_file"] = _imgs[scan_key]
        scan_fb = _fallbacks.get(scan_key, _fallbacks.get("SCAN", {}))
        if scan_fb:
            item["fallback_icon"] = scan_fb.get("icon", "")
            item["fallback_data_point"] = scan_fb.get("data_point", "")
        scan_items_data.append(item)

    scan_slot: Dict[str, Any] = {
        "type": "SCAN",
        "intro_copy": script_result.scan_intro,
        "items": scan_items_data,
        "audio_file": _audio_path("scan.mp3"),
        "words": scan_audio.word_timings if scan_audio else [],
        "duration_seconds": scan_audio.duration_seconds if scan_audio else 0.0,
    }
    # Slot-level image = first item's image (for intro)
    if _imgs.get("SCAN_0"):
        scan_slot["image_file"] = _imgs["SCAN_0"]
    if _fallbacks.get("SCAN_0") or _fallbacks.get("SCAN"):
        fb = _fallbacks.get("SCAN_0", _fallbacks.get("SCAN", {}))
        scan_slot["fallback_icon"] = fb.get("icon", "")
        scan_slot["fallback_data_point"] = fb.get("data_point", "")
    slots.append(scan_slot)

    # ---- WHY -----------------------------------------------------------------
    why_audio = audio_by_name.get("WHY")
    why_slot: Dict[str, Any] = {
        "type": "WHY",
        "copy": script_result.why,
        "audio_file": _audio_path("why.mp3"),
        "words": why_audio.word_timings if why_audio else [],
        "duration_seconds": why_audio.duration_seconds if why_audio else 0.0,
        "gfx": {},
    }
    if _imgs.get("WHY"):
        why_slot["image_file"] = _imgs["WHY"]
    if _fallbacks.get("WHY"):
        why_slot["fallback_icon"] = _fallbacks["WHY"].get("icon", "")
        why_slot["fallback_data_point"] = _fallbacks["WHY"].get("data_point", "")
    slots.append(why_slot)

    # ---- CLOSE ---------------------------------------------------------------
    close_audio = audio_by_name.get("CLOSE")
    close_slot: Dict[str, Any] = {
        "type": "CLOSE",
        "copy": script_result.close,
        "audio_file": _audio_path("close.mp3"),
        "words": close_audio.word_timings if close_audio else [],
        "duration_seconds": close_audio.duration_seconds if close_audio else 0.0,
        "gfx": {},
    }
    # No image for CLOSE slot (centered wordmark only)
    slots.append(close_slot)

    return slots


def _build_clips(script_result: ScriptResult) -> List[Dict[str, Any]]:
    """Build the clip definitions for extractable social cuts."""
    clips: List[Dict[str, Any]] = []

    # C1 — Lead story deep-dive (HOOK + LEAD + WHY tail)
    clips.append({
        "id": "C1",
        "title": "Lead Story",
        "slots": ["HOOK", "LEAD_COMPRESSED", "WHY_TAIL"],
        "platform_meta": script_result.platform_meta,
    })

    # C{idx+2} — One per scan item (index > 0)
    for idx in range(1, len(script_result.scan_cluster_ids)):
        clip_id = f"C{idx + 2}"
        clips.append({
            "id": clip_id,
            "title": f"Scan Item {idx + 1}",
            "slots": [f"SCAN_ITEM_{idx}"],
            "platform_meta": {},
        })

    # T0 — "Today in One Breath" (HOOK only)
    clips.append({
        "id": "T0",
        "title": "Today in One Breath",
        "slots": ["HOOK"],
        "platform_meta": {},
    })

    return clips


def _build_render_targets(clips: List[Dict[str, Any]]) -> List[str]:
    """Enumerate all render targets: full formats + clip IDs + thumbnail."""
    base_targets = ["anchor-16x9", "anchor-9x16"]
    clip_ids = [c["id"] for c in clips]
    return base_targets + clip_ids + ["thumbnail"]


def build_spec(
    extract_result: ExtractResult,
    script_result: ScriptResult,
    audio_result: AudioResult,
    audio_dir: str,
) -> Dict[str, Any]:
    """Assemble and return the Remotion JSON spec as a plain dict.

    The dict is fully JSON-serialisable (no bytes, no date objects).
    """
    log.info(
        "spec.build",
        brief_id=extract_result.brief_id,
        issue=extract_result.issue_number,
    )

    # Download validated news images using LLM-distilled search queries
    image_paths: Dict[str, str] = {}
    fallback_data: Dict[str, Dict[str, str]] = {}
    image_dir = os.path.join(os.path.dirname(audio_dir), "images")
    image_paths, fallback_data = _download_images(
        extract_result, script_result, image_dir, ANTHROPIC_API_KEY
    )

    slots = _build_slots(
        extract_result, script_result, audio_result, audio_dir,
        image_paths, fallback_data,
    )
    clips = _build_clips(script_result)
    render_targets = _build_render_targets(clips)

    spec: Dict[str, Any] = {
        "brief_id": extract_result.brief_id,
        "date": extract_result.brief_date.isoformat(),
        "issue_number": extract_result.issue_number,
        "slots": slots,
        "clips": clips,
        "render_targets": render_targets,
        "requires_review": audio_result.gate_result.requires_review,
        "unknown_words": audio_result.gate_result.unknown_words,
        "total_duration_seconds": audio_result.total_duration_seconds,
        "platform_meta": script_result.platform_meta,
    }

    log.info(
        "spec.done",
        brief_id=extract_result.brief_id,
        slot_count=len(slots),
        clip_count=len(clips),
        render_target_count=len(render_targets),
    )

    return spec


def save_spec(spec: Dict[str, Any], output_path: str) -> None:
    """Write *spec* as indented JSON to *output_path*, creating parent dirs.

    Wraps the spec in ``{"spec": ...}`` so Remotion's Composition schema
    (``z.object({spec: SpecSchema})``) can validate the ``--props`` file.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump({"spec": spec}, fh, indent=2)
    log.info("spec.saved", path=output_path)
