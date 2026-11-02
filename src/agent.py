from __future__ import annotations

import uuid
from dataclasses import asdict
from typing import Any

from src.audit import AuditLogger
from src.config import AppConfig
from src.gating import escalation_reason, evaluate_action_gate
from src.llm import maybe_generate_live_response
from src.models import (
    AgentResponse,
    ApprovalDecision,
    ApprovalRequest,
    Escalation,
    HumanOutcome,
    ProposedAction,
    SessionState,
)
from src.planner import plan_action
from src.tools import ToolRegistry, build_default_tool_registry


class Agent:
    def __init__(
        self,
        config: AppConfig,
        tools: ToolRegistry | None = None,
        session_id: str | None = None,
    ) -> None:
        self.config = config
        self.tools = tools or build_default_tool_registry()
        self.state = SessionState(session_id=session_id or str(uuid.uuid4()))
        self.audit = AuditLogger(
            path=config.audit_log_path,
            enable_hash_chain=config.enable_hash_chain,
        )

    def _next_sequence(self) -> int:
        self.state.sequence += 1
        return self.state.sequence

    def _log(self, event: str, payload: dict[str, Any]) -> None:
        self.audit.append(self.state.session_id, self._next_sequence(), event, payload)

    def _record_history(self, role: str, content: str) -> None:
        self.state.conversation_history.append({"role": role, "content": content})

    def _escalate(self, reason: str, user_message: str, priority: str = "normal") -> AgentResponse:
        payload = {
            "session_id": self.state.session_id,
            "conversation_history": self.state.conversation_history,
            "original_user_request": user_message,
            "escalation_reason": reason,
            "priority": priority,
        }

        if not self.config.human_available:
            self._log(
                "escalation",
                {
                    "reason": reason,
                    "handoff_target": "human_queue",
                    "status": "unavailable",
                },
            )
            message = "A human agent is currently unavailable, please try again later."
            self._record_history("assistant", message)
            return AgentResponse(status="escalation_unavailable", message=message)

        result = self.tools.execute(
            "escalate_to_human",
            {"queue_path": str(self.config.handoff_queue_path), "payload": payload},
        )
        escalation = Escalation(
            reason=reason,
            priority=priority,
            handoff_target=result["handoff_target"],
            payload=payload,
        )
        self.state.pending_escalation = escalation
        self._log(
            "escalation",
            {
                "reason": reason,
                "handoff_target": escalation.handoff_target,
                "status": "queued",
            },
        )
        message = "Your request has been escalated to a human support agent."
        self._record_history("assistant", message)
        return AgentResponse(status="escalated", message=message, escalation=escalation)

    def resolve_human_escalation(
        self,
        outcome: HumanOutcome,
        operator_id: str,
        notes: str,
    ) -> AgentResponse:
        pending = self.state.pending_escalation
        if pending is None:
            return AgentResponse(status="noop", message="No pending escalation to resolve.")

        self._log(
            "human_escalation_resolution",
            {
                "outcome": outcome,
                "operator_id": operator_id,
                "notes": notes,
                "escalation_reason": pending.reason,
            },
        )

        self.state.pending_escalation = None
        if outcome == "handled_externally":
            message = "This case was handled externally by the human team."
            self._record_history("assistant", message)
            return AgentResponse(status="resolved_externally", message=message)

        message = (
            "Human triage is complete; this case was returned to the assistant. "
            f"Human notes: {notes}"
        )
        self._record_history("assistant", message)
        return AgentResponse(status="returned_to_llm", message=message)

    def _execute_action(self, action: ProposedAction) -> AgentResponse:
        result = self.tools.execute(action.name, action.parameters)
        self._log(
            "execution_result",
            {
                "action": action.name,
                "parameters": action.parameters,
                "result": result,
            },
        )
        message = result.get("summary", "Action completed.")
        self._record_history("assistant", message)
        return AgentResponse(
            status="completed",
            message=message,
            executed_action=action.name,
            execution_result=result,
            requires_approval=False,
        )

    def handle_user_message(self, user_message: str) -> AgentResponse:
        self._record_history("user", user_message)

        action, ambiguous_intent = plan_action(user_message, self.config)
        forced_reason = escalation_reason(user_message, ambiguous_intent)
        if forced_reason:
            return self._escalate(reason=forced_reason, user_message=user_message, priority="high")

        if action is None:
            return self._escalate(
                reason="ambiguous_or_unresolvable",
                user_message=user_message,
                priority="normal",
            )

        self._log("proposal", {"action": action.name, "parameters": action.parameters})

        gate_decision = evaluate_action_gate(action, self.config)
        self._log(
            "risk_assessment",
            {
                "action": action.name,
                "confidence": action.confidence,
                "risk_level": action.risk_level,
                "sensitive_capability": action.sensitive_capability,
                "gate_status": gate_decision.status,
                "gate_reason": gate_decision.reason,
            },
        )

        if gate_decision.status == "pending_approval":
            self.state.pending_action = action
            approval_request = ApprovalRequest(
                action=action.name,
                parameters=action.parameters,
                risk_reason=gate_decision.reason,
                confidence=action.confidence,
            )
            self._log("approval_request", asdict(approval_request))
            message = f"Approval required for action `{action.name}` due to {gate_decision.reason}."
            self._record_history("assistant", message)
            return AgentResponse(
                status="pending_approval",
                message=message,
                requires_approval=True,
                approval_request=approval_request,
            )

        return self._execute_action(action)

    def apply_human_decision(self, decision: ApprovalDecision) -> AgentResponse:
        pending = self.state.pending_action
        if pending is None:
            message = "No pending action to approve or deny."
            return AgentResponse(status="noop", message=message)

        self._log(
            "human_decision",
            {
                "verdict": decision.verdict,
                "approver_id": decision.approver_id,
                "reason": decision.reason,
                "edited_parameters": decision.edited_parameters,
            },
        )

        if decision.verdict == "deny":
            self.state.pending_action = None
            message = "Action denied by human reviewer. Proceeding without that step."
            self._record_history("assistant", message)
            return AgentResponse(status="denied", message=message)

        if decision.verdict == "escalate":
            return self._escalate(
                reason="human_verdict_escalate",
                user_message=self.state.conversation_history[-1]["content"],
                priority="high",
            )

        if decision.verdict == "edit_parameters" and decision.edited_parameters:
            pending.parameters = _validate_and_merge_parameters(
                pending.name,
                pending.parameters,
                decision.edited_parameters,
            )

        self.state.pending_action = None
        return self._execute_action(pending)

    def get_live_or_cached_assistant_text(self, user_message: str, fallback: str) -> str:
        live_text = maybe_generate_live_response(self.config, user_message)
        return live_text or fallback


def _validate_and_merge_parameters(
    action_name: str,
    current: dict[str, Any],
    edited: dict[str, Any],
) -> dict[str, Any]:
    merged = {**current, **edited}

    if action_name == "issue_refund":
        amount = float(merged["amount"])
        if amount <= 0:
            raise ValueError("Refund amount must be positive.")
        merged["amount"] = amount

    return merged

