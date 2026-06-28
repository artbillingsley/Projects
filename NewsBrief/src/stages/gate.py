# src/stages/gate.py
from __future__ import annotations

from enum import Enum

import structlog

log = structlog.get_logger()


class GateDecision(Enum):
    AUTO = "auto"
    APPROVED = "approved"
    BLOCKED = "blocked"
    KILLED = "killed"

    @property
    def should_publish(self) -> bool:
        return self in (GateDecision.AUTO, GateDecision.APPROVED)


def check_gate(
    publish_mode: str,
    requires_review: bool,
    approved: bool = False,
    killed: bool = False,
) -> GateDecision:
    log.info("gate.check", mode=publish_mode, requires_review=requires_review, approved=approved, killed=killed)

    # requires_review overrides auto mode (R8 proper-noun gate)
    if requires_review and not approved:
        log.warning("gate.blocked.review_required")
        return GateDecision.BLOCKED

    if publish_mode == "preview":
        if approved:
            return GateDecision.APPROVED
        log.info("gate.blocked.preview_mode")
        return GateDecision.BLOCKED

    if publish_mode == "gate":
        if killed:
            return GateDecision.KILLED
        return GateDecision.AUTO

    if publish_mode == "auto":
        return GateDecision.AUTO

    log.warning("gate.unknown_mode", mode=publish_mode)
    return GateDecision.BLOCKED
