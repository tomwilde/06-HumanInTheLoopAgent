from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Verdict = Literal["approve", "deny", "edit_parameters", "escalate"]
HumanOutcome = Literal["return_to_llm", "handled_externally"]
RiskLevel = Literal["low", "high"]


@dataclass(slots=True)
class ProposedAction:
    name: str
    parameters: dict[str, Any]
    confidence: float
    risk_level: RiskLevel
    risk_reason: str
    sensitive_capability: str | None = None


@dataclass(slots=True)
class ApprovalRequest:
    action: str
    parameters: dict[str, Any]
    risk_reason: str
    confidence: float


@dataclass(slots=True)
class Escalation:
    reason: str
    priority: str
    handoff_target: str
    payload: dict[str, Any]


@dataclass(slots=True)
class AgentResponse:
    status: str
    message: str
    executed_action: str | None = None
    execution_result: dict[str, Any] | None = None
    requires_approval: bool = False
    approval_request: ApprovalRequest | None = None
    escalation: Escalation | None = None


@dataclass(slots=True)
class ApprovalDecision:
    verdict: Verdict
    approver_id: str
    reason: str
    edited_parameters: dict[str, Any] | None = None


@dataclass(slots=True)
class SessionState:
    session_id: str
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    pending_action: ProposedAction | None = None
    pending_escalation: Escalation | None = None
    sequence: int = 0

