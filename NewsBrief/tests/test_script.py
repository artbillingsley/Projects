# tests/test_script.py
import json
from datetime import date
from unittest.mock import MagicMock

import pytest

from src.stages.extract import ClusterData, ExtractResult


def _make_extract_result(sample_brief_data) -> ExtractResult:
    clusters = [
        ClusterData(
            id=c["id"],
            cif_code=c["cif_code"],
            headline=c["headline"],
            body=c["body"],
            why_this_matters=c["why_this_matters"] or "",
            what_changed=c.get("what_changed"),
            status=c["status"],
            confidence=c["confidence"],
            position=c["position"],
            sources=c["sources"],
        )
        for c in sample_brief_data["clusters"]
    ]
    return ExtractResult(
        brief_id=sample_brief_data["brief_id"],
        issue_number=sample_brief_data["issue_number"],
        brief_date=sample_brief_data["brief_date"],
        clusters=clusters,
    )


def test_generate_script_returns_script_result(sample_brief_data):
    from src.stages.script import generate_script, ScriptResult

    extract_result = _make_extract_result(sample_brief_data)

    lead_id = sample_brief_data["clusters"][0]["id"]
    scan_ids = [sample_brief_data["clusters"][i]["id"] for i in [2, 3, 4, 5]]

    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text=json.dumps(
                {
                    "lead_cluster_id": lead_id,
                    "scan_cluster_ids": scan_ids,
                    "selection_rationale": "Lead with Hormuz (DEVELOPING, highest stakes).",
                    "hook": "An American helicopter is down near the Strait of Hormuz.",
                    "lead": "Iran shot down a U.S. Army Apache near the Strait of Hormuz.",
                    "scan_intro": "Four more, fast.",
                    "scan_items": [
                        "One. The House sent Trump a $70 billion immigration bill.",
                        "Two. Trump put a housing regulator atop the intelligence community.",
                        "Three. Gas sits at $4.16 a gallon.",
                        "Four. OpenAI filed to go public above $850 billion.",
                    ],
                    "why": "Here is the thread. The war near Hormuz is the same war showing up in your gas tank.",
                    "close": "That is the brief for June tenth. Every source shown. Every claim tagged. The full record is linked below. Decide.",
                    "platform_meta": {
                        "youtube_title": "COGNOSCERE Daily Brief - June 10, 2026",
                    },
                }
            )
        )
    ]
    mock_response.usage = MagicMock(input_tokens=4200, output_tokens=1800)

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    result = generate_script(extract_result, client=mock_client)

    assert isinstance(result, ScriptResult)
    assert result.lead_cluster_id == lead_id
    assert result.scan_cluster_ids == scan_ids
    assert "Hormuz" in result.hook
    assert result.input_tokens == 4200
    assert result.output_tokens == 1800
    mock_client.messages.create.assert_called_once()


def test_generate_script_uses_correct_model(sample_brief_data):
    from src.stages.script import generate_script

    extract_result = _make_extract_result(sample_brief_data)

    scan_ids = [sample_brief_data["clusters"][i]["id"] for i in [2, 3, 4]]

    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text=json.dumps(
                {
                    "lead_cluster_id": sample_brief_data["clusters"][0]["id"],
                    "scan_cluster_ids": scan_ids,
                    "selection_rationale": "test",
                    "hook": "hook",
                    "lead": "lead",
                    "scan_intro": "intro",
                    "scan_items": ["One. item1", "Two. item2", "Three. item3"],
                    "why": "why",
                    "close": "close",
                    "platform_meta": {},
                }
            )
        )
    ]
    mock_response.usage = MagicMock(input_tokens=100, output_tokens=100)

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    generate_script(extract_result, client=mock_client)

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-20250514"


def test_generate_script_raises_on_invalid_json(sample_brief_data):
    from src.stages.script import generate_script, ScriptError

    extract_result = _make_extract_result(sample_brief_data)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="not valid json {{{")]
    mock_response.usage = MagicMock(input_tokens=100, output_tokens=100)

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with pytest.raises(ScriptError, match="Failed to parse"):
        generate_script(extract_result, client=mock_client)
