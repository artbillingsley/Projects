# src/stages/extract.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List

import structlog
from sqlalchemy.orm import Session

from src.models import Brief, Cluster

log = structlog.get_logger()

# ---- Source name mapping ---------------------------------------------------
# Collector/API names -> clean editorial names shown on-screen.
_SOURCE_MAP = {
    "reuters": "Reuters",
    "ap": "Associated Press",
    "bbc": "BBC News",
    "nyt": "The New York Times",
    "wsj": "Wall Street Journal",
    "wapo": "Washington Post",
    "bloomberg": "Bloomberg",
    "ft": "Financial Times",
    "aljazeera": "Al Jazeera",
    "guardian": "The Guardian",
    "latimes": "Los Angeles Times",
    "bostonglobe": "Boston Globe",
    "militarytimes": "Military Times",
    "rand": "RAND",
    "csis": "CSIS",
}


def _clean_sources(raw_names: list) -> list:
    """Map collector names to editorial names, deduplicate, limit to 4."""
    seen: set[str] = set()
    clean: list[str] = []
    for name in raw_names:
        mapped = _SOURCE_MAP.get(name.lower().strip(), None)
        if mapped and mapped not in seen:
            seen.add(mapped)
            clean.append(mapped)
    return clean[:4]


class ExtractError(Exception):
    pass


@dataclass
class ClusterData:
    id: str           # UUID string
    cif_code: str     # e.g. "DX9F"
    headline: str
    body: str
    why_this_matters: str
    what_changed: str | None
    status: str
    confidence: str
    position: int
    sources: List[str]
    source_urls: List[str] = field(default_factory=list)


@dataclass
class ExtractResult:
    brief_id: str     # date string used as ID, e.g. "2026-06-10"
    issue_number: str
    brief_date: date
    clusters: List[ClusterData]


def extract(session: Session, run_date: date) -> ExtractResult:
    log.info("extract.start", run_date=str(run_date))

    brief = session.query(Brief).filter(Brief.brief_date == run_date).first()

    if brief is None:
        raise ExtractError(f"No brief found for {run_date}")

    # Get cluster UUIDs from the brief's JSON array
    cluster_uuids = brief.cluster_ids or []

    if not cluster_uuids:
        raise ExtractError(
            f"Brief {brief.issue_number} ({brief.brief_date}) has no stories."
        )

    # Fetch all clusters in one query
    clusters_by_id = {}
    db_clusters = (
        session.query(Cluster).filter(Cluster.cluster_id.in_(cluster_uuids)).all()
    )
    for c in db_clusters:
        clusters_by_id[c.cluster_id] = c

    # Build result in brief's cluster_ids order (preserves editorial ordering)
    clusters = []
    for position, uuid in enumerate(cluster_uuids, 1):
        c = clusters_by_id.get(uuid)
        if c is None:
            continue
        clusters.append(
            ClusterData(
                id=c.cluster_id,          # UUID string
                cif_code=c.cif_code,      # e.g. "DX9F"
                headline=c.headline,
                body=c.summary,           # actual field is 'summary'
                why_this_matters=c.why_this_matters or "",
                what_changed=c.what_changed,
                status=c.status or "NEW",
                confidence=c.confidence or "High",
                position=position,
                sources=_clean_sources([s.name for s in c.sources]),
                source_urls=[s.url for s in c.sources],
            )
        )

    issue_str = f"N{brief.issue_number}" if brief.issue_number else "N000"

    log.info(
        "extract.done",
        brief_date=str(brief.brief_date),
        issue=issue_str,
        cluster_count=len(clusters),
    )

    return ExtractResult(
        brief_id=str(brief.brief_date),   # use date string as ID
        issue_number=issue_str,
        brief_date=brief.brief_date,
        clusters=clusters,
    )
