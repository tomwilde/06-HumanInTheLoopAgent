from __future__ import annotations

from dataclasses import dataclass

from src.config import AppConfig
from src.models import ProposedAction


@dataclass(slots=True)
class GateDecision:
    status: str
    reason: str


HUMAN_KEYWORDS = {"human", "manager", "complaint", "person", "representative"}


def escalation_reason(user_message: str, ambiguous_intent: bool) -> str | None:
    lowered = user_message.lower()
    if any(keyword in lowered for keyword in HUMAN_KEYWORDS):
        return "explicit_human_request"
    if ambiguous_intent:
        return "ambiguous_or_unresolvable"
    return None


def evaluate_action_gate(action: ProposedAction, config: AppConfig) -> GateDecision:
    if action.confidence < config.confidence_threshold:
        return GateDecision(status="pending_approval", reason="low_confidence")

    if action.risk_level == "high":
        return GateDecision(status="pending_approval", reason="high_risk_action")

    if action.sensitive_capability and action.sensitive_capability in config.sensitive_capabilities:
        return GateDecision(status="pending_approval", reason="sensitive_capability")

    return GateDecision(status="auto_execute", reason="safe_action")

