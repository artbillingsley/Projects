# tests/test_gate.py
import pytest


def test_gate_preview_mode_blocks():
    from src.stages.gate import check_gate, GateDecision

    decision = check_gate(
        publish_mode="preview",
        requires_review=False,
        approved=False,
    )
    assert decision == GateDecision.BLOCKED
    assert not decision.should_publish


def test_gate_preview_mode_with_approve_passes():
    from src.stages.gate import check_gate, GateDecision

    decision = check_gate(
        publish_mode="preview",
        requires_review=False,
        approved=True,
    )
    assert decision == GateDecision.APPROVED


def test_gate_auto_mode_passes():
    from src.stages.gate import check_gate, GateDecision

    decision = check_gate(
        publish_mode="auto",
        requires_review=False,
        approved=False,
    )
    assert decision == GateDecision.AUTO


def test_gate_auto_mode_blocked_by_review_flag():
    from src.stages.gate import check_gate, GateDecision

    decision = check_gate(
        publish_mode="auto",
        requires_review=True,
        approved=False,
    )
    assert decision == GateDecision.BLOCKED


def test_gate_mode_passes_without_kill():
    from src.stages.gate import check_gate, GateDecision

    decision = check_gate(
        publish_mode="gate",
        requires_review=False,
        approved=False,
        killed=False,
    )
    assert decision == GateDecision.AUTO


def test_gate_mode_blocked_by_kill():
    from src.stages.gate import check_gate, GateDecision

    decision = check_gate(
        publish_mode="gate",
        requires_review=False,
        approved=False,
        killed=True,
    )
    assert decision == GateDecision.KILLED
