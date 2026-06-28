# tests/test_extract.py
from datetime import date
from unittest.mock import MagicMock, call

import pytest


def test_extract_returns_brief_and_clusters(sample_brief_data):
    from src.stages.extract import extract, ExtractResult

    mock_session = MagicMock()

    # Mock the Brief object
    mock_brief = MagicMock()
    mock_brief.brief_date = sample_brief_data["brief_date"]
    mock_brief.issue_number = 103
    mock_brief.cluster_ids = sample_brief_data["cluster_ids"]

    # Mock Cluster objects
    mock_db_clusters = []
    for c in sample_brief_data["clusters"]:
        mc = MagicMock()
        mc.cluster_id = c["id"]
        mc.cif_code = c["cif_code"]
        mc.headline = c["headline"]
        mc.summary = c["body"]
        mc.why_this_matters = c["why_this_matters"]
        mc.what_changed = c["what_changed"]
        mc.status = c["status"]
        mc.confidence = c["confidence"]
        mc.sources = [MagicMock(name=s) for s in c["sources"]]
        mock_db_clusters.append(mc)

    # Wire up session.query(...).filter(...).first() for Brief
    # and session.query(...).filter(...).all() for Cluster
    brief_query = MagicMock()
    brief_query.filter.return_value.first.return_value = mock_brief

    cluster_query = MagicMock()
    cluster_query.filter.return_value.all.return_value = mock_db_clusters

    from src.models import Brief, Cluster

    def query_side_effect(model):
        if model is Brief:
            return brief_query
        if model is Cluster:
            return cluster_query
        return MagicMock()

    mock_session.query.side_effect = query_side_effect

    result = extract(mock_session, run_date=date(2026, 6, 10))

    assert isinstance(result, ExtractResult)
    assert result.brief_id == "2026-06-10"
    assert result.issue_number == "N103"
    assert len(result.clusters) == 6


def test_extract_aborts_when_no_brief_found():
    from src.stages.extract import extract, ExtractError

    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(ExtractError, match="No brief found"):
        extract(mock_session, run_date=date(2026, 6, 10))


def test_extract_aborts_when_brief_has_no_clusters():
    from src.stages.extract import extract, ExtractError

    mock_session = MagicMock()
    mock_brief = MagicMock()
    mock_brief.brief_date = date(2026, 6, 10)
    mock_brief.cluster_ids = []
    mock_session.query.return_value.filter.return_value.first.return_value = mock_brief

    with pytest.raises(ExtractError, match="no stories"):
        extract(mock_session, run_date=date(2026, 6, 10))


def test_extract_preserves_editorial_order(sample_brief_data):
    """Clusters should be returned in the order defined by brief.cluster_ids."""
    from src.stages.extract import extract

    mock_session = MagicMock()

    mock_brief = MagicMock()
    mock_brief.brief_date = sample_brief_data["brief_date"]
    mock_brief.issue_number = 103
    # Reverse the cluster_ids order to test ordering
    reversed_ids = list(reversed(sample_brief_data["cluster_ids"]))
    mock_brief.cluster_ids = reversed_ids

    mock_db_clusters = []
    for c in sample_brief_data["clusters"]:
        mc = MagicMock()
        mc.cluster_id = c["id"]
        mc.cif_code = c["cif_code"]
        mc.headline = c["headline"]
        mc.summary = c["body"]
        mc.why_this_matters = c["why_this_matters"]
        mc.what_changed = c["what_changed"]
        mc.status = c["status"]
        mc.confidence = c["confidence"]
        mc.sources = []
        mock_db_clusters.append(mc)

    from src.models import Brief, Cluster

    brief_query = MagicMock()
    brief_query.filter.return_value.first.return_value = mock_brief

    cluster_query = MagicMock()
    cluster_query.filter.return_value.all.return_value = mock_db_clusters

    def query_side_effect(model):
        if model is Brief:
            return brief_query
        if model is Cluster:
            return cluster_query
        return MagicMock()

    mock_session.query.side_effect = query_side_effect

    result = extract(mock_session, run_date=date(2026, 6, 10))

    # First cluster in result should correspond to last entry in original list
    assert result.clusters[0].id == reversed_ids[0]
    # Positions should be 1-indexed sequential
    assert result.clusters[0].position == 1
    assert result.clusters[1].position == 2
