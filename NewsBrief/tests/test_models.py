# tests/test_models.py
from datetime import date, datetime


def test_brief_model_fields():
    from src.models import Brief

    b = Brief(
        brief_date=date(2026, 6, 10),
        methodology_version="v3.2",
        issue_number=103,
        one_breath="A brief summary.",
        cluster_ids=["uuid-1", "uuid-2"],
        scan_layer={},
        published_at=None,
        created_at=datetime(2026, 6, 10, 0, 0, 0),
        updated_at=datetime(2026, 6, 10, 0, 0, 0),
    )
    assert b.issue_number == 103
    assert b.brief_date == date(2026, 6, 10)


def test_cluster_model_fields():
    from src.models import Cluster

    c = Cluster(
        cluster_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        cif_code="DX9F",
        first_seen=date(2026, 6, 10),
        headline="U.S. and Iran Trade Strikes",
        summary="Iran shot down...",
        why_this_matters="The Strait carries...",
        what_changed="Iran struck U.S. bases...",
        status="DEVELOPING",
        confidence="High",
        word_count=120,
        tier=1,
    )
    assert c.headline == "U.S. and Iran Trade Strikes"
    assert c.status == "DEVELOPING"
    assert c.cif_code == "DX9F"


def test_video_run_model_fields():
    from src.models import VideoRun

    vr = VideoRun(
        id="vr-2026-06-10",
        brief_date=date(2026, 6, 10),
        issue_number="N103",
        run_date=date(2026, 6, 10),
        started_at=datetime(2026, 6, 10, 12, 0, 0),
        status="running",
    )
    assert vr.id == "vr-2026-06-10"
    assert vr.status == "running"


def test_video_script_model_fields():
    from src.models import VideoScript

    vs = VideoScript(
        run_id="vr-2026-06-10",
        brief_date=date(2026, 6, 10),
        hook_copy="An American helicopter is down.",
        lead_copy="Iran shot down a U.S. Army Apache.",
        scan_copy="Four more, fast.",
        why_copy="Here is the thread.",
        close_copy="That is the brief.",
        lead_cluster_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        scan_cluster_ids=["uuid-2", "uuid-3", "uuid-4", "uuid-5"],
    )
    assert vs.hook_copy == "An American helicopter is down."
    assert vs.scan_cluster_ids == ["uuid-2", "uuid-3", "uuid-4", "uuid-5"]
