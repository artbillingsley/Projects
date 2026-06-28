# tests/conftest.py
from datetime import date, datetime

import pytest

from src.config import Config


@pytest.fixture
def sample_config():
    return Config(
        db_host="localhost",
        db_port=3306,
        db_user="test",
        db_password="test",
        db_name="testdb",
        anthropic_api_key="sk-ant-test",
        publish_mode="preview",
    )


@pytest.fixture
def sample_brief_data():
    """Raw dict matching the shape of a Brief + Clusters from the DB."""
    return {
        "brief_id": "2026-06-10",
        "issue_number": "N103",
        "brief_date": date(2026, 6, 10),
        "cluster_ids": [
            "aaaaaaaa-0001-0001-0001-000000000001",
            "aaaaaaaa-0002-0002-0002-000000000002",
            "aaaaaaaa-0003-0003-0003-000000000003",
            "aaaaaaaa-0004-0004-0004-000000000004",
            "aaaaaaaa-0005-0005-0005-000000000005",
            "aaaaaaaa-0010-0010-0010-000000000010",
        ],
        "clusters": [
            {
                "id": "aaaaaaaa-0001-0001-0001-000000000001",
                "cif_code": "AA01",
                "headline": "U.S. and Iran Trade Strikes After Apache Helicopter Downed Near Strait of Hormuz",
                "body": "Iran shot down a U.S. Army Apache helicopter near the Strait of Hormuz...",
                "why_this_matters": "The Strait of Hormuz carries roughly a fifth of the world's oil.",
                "what_changed": "Iran struck U.S. military bases in Bahrain, Jordan, and Kuwait.",
                "status": "DEVELOPING",
                "confidence": "High",
                "position": 1,
                "sources": ["Reuters", "Associated Press", "Wall Street Journal"],
            },
            {
                "id": "aaaaaaaa-0002-0002-0002-000000000002",
                "cif_code": "BB02",
                "headline": "Trump and Netanyahu's Iran War Has Stalled, Raising Fears of a Lasting Regional Crisis",
                "body": "A month after the United States and Israel launched joint airstrikes...",
                "why_this_matters": "Oil prices and Strait of Hormuz shipping lanes remain in play.",
                "what_changed": None,
                "status": "NEW",
                "confidence": "High",
                "position": 2,
                "sources": ["BBC News", "The New York Times", "Reuters"],
            },
            {
                "id": "aaaaaaaa-0003-0003-0003-000000000003",
                "cif_code": "CC03",
                "headline": "House Sends $70 Billion Immigration Enforcement Bill to Trump",
                "body": "The Republican-controlled House passed a $70 billion immigration enforcement bill...",
                "why_this_matters": "ICE and Border Patrol funded through 2029. No new oversight.",
                "what_changed": None,
                "status": "NEW",
                "confidence": "High",
                "position": 3,
                "sources": ["Reuters", "Associated Press", "Los Angeles Times"],
            },
            {
                "id": "aaaaaaaa-0004-0004-0004-000000000004",
                "cif_code": "DD04",
                "headline": "Trump installs housing regulator Bill Pulte as acting intelligence director",
                "body": "President Trump is pressing ahead with his appointment of Bill Pulte...",
                "why_this_matters": "Section 702 surveillance law may lapse this week.",
                "what_changed": None,
                "status": "NEW",
                "confidence": "High",
                "position": 4,
                "sources": ["Reuters", "The Guardian", "Associated Press"],
            },
            {
                "id": "aaaaaaaa-0005-0005-0005-000000000005",
                "cif_code": "EE05",
                "headline": 'Trump calls US gas prices "not very high" as national average sits $1 above last year',
                "body": "Gas prices are running about a dollar more per gallon...",
                "why_this_matters": "Filling a 15-gallon tank costs $15 more than a year ago.",
                "what_changed": None,
                "status": "NEW",
                "confidence": "High",
                "position": 5,
                "sources": ["Reuters", "AAA via The Guardian", "Bloomberg"],
            },
            {
                "id": "aaaaaaaa-0010-0010-0010-000000000010",
                "cif_code": "FF10",
                "headline": "OpenAI files confidential IPO paperwork with SEC, targeting valuation above $850 billion",
                "body": "OpenAI confirmed Monday it has submitted a confidential S-1 filing...",
                "why_this_matters": "Three of the most valuable private companies are moving to public markets.",
                "what_changed": "OpenAI confirmed its own confidential S-1 filing.",
                "status": "DEVELOPING",
                "confidence": "High",
                "position": 6,
                "sources": ["Reuters", "The Guardian", "Wall Street Journal"],
            },
        ],
    }
