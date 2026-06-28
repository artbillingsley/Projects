# src/stages/extract_tech.py
"""Extract articles from the DRS SQLite database for the TechBrief."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date
from typing import List

import structlog

log = structlog.get_logger()

DRS_DB_PATH = "/home/ec2-user/drs/drs.db"


@dataclass
class TechArticle:
    title: str
    summary: str
    domain: str  # IT, AI, DS
    urgency: str  # ACT, PREPARE, WATCH
    source_name: str
    source_url: str
    relevance_score: float
    tags: List[str] = field(default_factory=list)


@dataclass
class TechExtractResult:
    brief_date: date
    issue_number: str
    articles: List[TechArticle]
    act_count: int
    prepare_count: int
    watch_count: int

    @property
    def brief_id(self) -> str:
        return self.brief_date.isoformat()


def extract_tech(run_date: date) -> TechExtractResult:
    """Extract top articles from DRS for the TechBrief."""
    log.info("extract_tech.start", run_date=str(run_date))

    conn = sqlite3.connect(DRS_DB_PATH)
    cursor = conn.cursor()

    # Get articles from last 36 hours, prioritized by urgency then relevance
    cursor.execute("""
        SELECT a.title, a.summary, a.domain, a.urgency, a.source_name,
               a.source_url, a.relevance_score
        FROM articles a
        WHERE a.collected_at >= datetime('now', '-36 hours')
        ORDER BY
            CASE a.urgency WHEN 'ACT' THEN 1 WHEN 'PREPARE' THEN 2 WHEN 'WATCH' THEN 3 ELSE 4 END,
            a.relevance_score DESC
        LIMIT 12
    """)

    articles = []
    for row in cursor.fetchall():
        # Get tags for this article
        cursor.execute("""
            SELECT tag FROM article_tags
            WHERE article_id = (SELECT id FROM articles WHERE title = ? LIMIT 1)
        """, (row[0],))
        tags = [t[0] for t in cursor.fetchall()]

        articles.append(TechArticle(
            title=row[0],
            summary=row[1],
            domain=row[2],
            urgency=row[3],
            source_name=row[4],
            source_url=row[5] or "",
            relevance_score=row[6],
            tags=tags,
        ))

    # Get issue number — sequential count with offset to match DRS numbering
    # DRS issue T146 = run #49 in this DB, so offset = 97
    DRS_ISSUE_OFFSET = 97
    cursor.execute("SELECT COUNT(*) FROM collection_runs")
    run_count = cursor.fetchone()[0]
    issue_number = f"T{run_count + DRS_ISSUE_OFFSET}"

    conn.close()

    act_count = sum(1 for a in articles if a.urgency == "ACT")
    prepare_count = sum(1 for a in articles if a.urgency == "PREPARE")
    watch_count = sum(1 for a in articles if a.urgency == "WATCH")

    log.info(
        "extract_tech.done",
        article_count=len(articles),
        act=act_count,
        prepare=prepare_count,
        watch=watch_count,
        issue=issue_number,
    )

    return TechExtractResult(
        brief_date=run_date,
        issue_number=issue_number,
        articles=articles,
        act_count=act_count,
        prepare_count=prepare_count,
        watch_count=watch_count,
    )
