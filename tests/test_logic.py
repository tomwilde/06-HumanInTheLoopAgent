from src.agent import Agent, ApprovalDecision
from src.config import AppConfig


def test_safe_lookup_executes_without_human(tmp_path):
    config = AppConfig(
        audit_log_path=tmp_path / "audit.jsonl",
        handoff_queue_path=tmp_path / "queue.jsonl",
    )
    agent = Agent(config=config)

    response = agent.handle_user_message("lookup order 123")

    assert response.status == "completed"
    assert response.executed_action == "lookup_order"
    assert response.requires_approval is False


def test_high_risk_refund_pauses_for_approval(tmp_path):
    config = AppConfig(
        confidence_threshold=0.8,
        refund_limit=50.0,
        audit_log_path=tmp_path / "audit.jsonl",
        handoff_queue_path=tmp_path / "queue.jsonl",
    )
    agent = Agent(config=config)

    response = agent.handle_user_message("refund order 123 amount 200")

    assert response.status == "pending_approval"
    assert response.requires_approval is True
    assert response.approval_request is not None
    assert response.approval_request.risk_reason == "high_risk_action"


def test_explicit_human_request_escalates(tmp_path):
    config = AppConfig(
        audit_log_path=tmp_path / "audit.jsonl",
        handoff_queue_path=tmp_path / "queue.jsonl",
    )
    agent = Agent(config=config)

    response = agent.handle_user_message("I want to speak to a human manager")

    assert response.status == "escalated"
    assert response.escalation is not None
    assert response.escalation.reason == "explicit_human_request"


def test_human_edit_then_approve_merges_parameters(tmp_path):
    config = AppConfig(
        refund_limit=50.0,
        audit_log_path=tmp_path / "audit.jsonl",
        handoff_queue_path=tmp_path / "queue.jsonl",
    )
    agent = Agent(config=config)

    first = agent.handle_user_message("refund order 123 amount 75")
    assert first.status == "pending_approval"

    resumed = agent.apply_human_decision(
        ApprovalDecision(
            verdict="edit_parameters",
            approver_id="agent-1",
            reason="limit adjustment",
            edited_parameters={"amount": 25.0},
        )
    )

    assert resumed.status == "completed"
    assert resumed.executed_action == "issue_refund"
    assert resumed.execution_result is not None
    assert resumed.execution_result["amount"] == 25.0


def test_no_human_available_returns_fallback(tmp_path):
    config = AppConfig(
        human_available=False,
        audit_log_path=tmp_path / "audit.jsonl",
        handoff_queue_path=tmp_path / "queue.jsonl",
    )
    agent = Agent(config=config)

    response = agent.handle_user_message("human")

    assert response.status == "escalation_unavailable"
    assert "currently unavailable" in response.message


def test_human_panel_can_resolve_escalation_externally(tmp_path):
    config = AppConfig(
        audit_log_path=tmp_path / "audit.jsonl",
        handoff_queue_path=tmp_path / "queue.jsonl",
    )
    agent = Agent(config=config)

    escalated = agent.handle_user_message("human please")
    assert escalated.status == "escalated"
    assert agent.state.pending_escalation is not None

    outcome = agent.resolve_human_escalation(
        outcome="handled_externally",
        operator_id="human-ops-1",
        notes="Called user and solved manually.",
    )

    assert outcome.status == "resolved_externally"
    assert agent.state.pending_escalation is None
    assert "handled externally" in outcome.message.lower()


def test_human_panel_can_return_escalation_back_to_llm(tmp_path):
    config = AppConfig(
        audit_log_path=tmp_path / "audit.jsonl",
        handoff_queue_path=tmp_path / "queue.jsonl",
    )
    agent = Agent(config=config)

    escalated = agent.handle_user_message("manager please")
    assert escalated.status == "escalated"

    notes = "Send back for automated follow-up."
    outcome = agent.resolve_human_escalation(
        outcome="return_to_llm",
        operator_id="human-ops-2",
        notes=notes,
    )

    assert outcome.status == "returned_to_llm"
    assert agent.state.pending_escalation is None
    assert "returned to the assistant" in outcome.message.lower()
    assert notes in outcome.message

