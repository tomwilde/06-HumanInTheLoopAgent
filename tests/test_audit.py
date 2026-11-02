import json

from src.agent import Agent, ApprovalDecision
from src.config import AppConfig


def test_audit_log_contains_monotonic_sequence_and_escalation(tmp_path):
    audit_path = tmp_path / "audit.jsonl"
    queue_path = tmp_path / "queue.jsonl"
    config = AppConfig(
        audit_log_path=audit_path,
        handoff_queue_path=queue_path,
        enable_hash_chain=True,
    )
    agent = Agent(config=config)

    agent.handle_user_message("lookup order 123")
    agent.handle_user_message("refund order 123 amount 75")
    agent.apply_human_decision(
        ApprovalDecision(verdict="approve", approver_id="lead-1", reason="valid")
    )
    agent.handle_user_message("human")

    rows = [json.loads(line) for line in audit_path.read_text().splitlines()]

    seqs = [row["sequence"] for row in rows]
    assert seqs == sorted(seqs)
    assert len(set(seqs)) == len(seqs)

    escalation_rows = [row for row in rows if row["event"] == "escalation"]
    assert escalation_rows
    assert escalation_rows[0]["reason"] == "explicit_human_request"
    assert escalation_rows[0]["handoff_target"] == "human_queue"
    assert all("timestamp" in row for row in rows)
    assert all("hash" in row for row in rows)

