from __future__ import annotations

import json
from typing import cast

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from src.agent import Agent, ApprovalDecision
from src.config import AppConfig
from src.models import HumanOutcome, Verdict


def _get_config() -> AppConfig:
    config = AppConfig.from_env()
    try:
        if "human_available" in st.secrets:
            config.human_available = str(st.secrets["human_available"]).lower() == "true"
    except StreamlitSecretNotFoundError:
        pass
    return config


def _init_agent() -> Agent:
    if "agent" not in st.session_state:
        st.session_state.agent = Agent(config=_get_config())
    return st.session_state.agent


def _render_history(agent: Agent) -> None:
    for message in agent.state.conversation_history:
        role = message["role"].capitalize()
        st.markdown(f"{role}: {message['content']}")


def _render_approval_panel(agent: Agent) -> None:
    pending = agent.state.pending_action
    if pending is None:
        return

    st.markdown("### Approval required")
    params_json = json.dumps(pending.parameters)
    st.markdown(
        f"Proposed action: `{pending.name}` with params `{params_json}` "
        f"and confidence `{pending.confidence}`"
    )
    verdict = st.selectbox(
        "Verdict",
        options=["approve", "deny", "edit_parameters", "escalate"],
        key="verdict",
    )
    approver_id = st.text_input("Approver ID", value="reviewer-1", key="approver_id")
    decision_reason = st.text_input("Reason", value="reviewed", key="decision_reason")
    edited_params_json = st.text_input(
        "Edited Parameters (JSON)",
        value="{}",
        key="edited_params_json",
    )

    if st.button("Submit decision", key="submit_decision"):
        edited_params = json.loads(edited_params_json)
        typed_verdict = cast(Verdict, verdict)
        decision = ApprovalDecision(
            verdict=typed_verdict,
            approver_id=approver_id,
            reason=decision_reason,
            edited_parameters=edited_params,
        )
        result = agent.apply_human_decision(decision)
        st.markdown(f"Assistant: {result.message}")
        st.rerun()


def _render_human_interaction_panel(agent: Agent) -> None:
    pending_escalation = agent.state.pending_escalation

    if pending_escalation is None:
        st.markdown("No escalation pending.")
        return

    st.markdown(f"Reason: `{pending_escalation.reason}`")
    st.markdown(f"Priority: `{pending_escalation.priority}`")
    outcome = st.selectbox(
        "Outcome",
        options=["return_to_llm", "handled_externally"],
        key="human_outcome",
    )
    operator_id = st.text_input("Operator ID", value="human-ops-1", key="human_operator_id")
    notes = st.text_area("Human Notes", value="", key="human_notes")

    if st.button("Apply Human Outcome", key="human_submit"):
        typed_outcome = cast(HumanOutcome, outcome)
        result = agent.resolve_human_escalation(
            outcome=typed_outcome,
            operator_id=operator_id,
            notes=notes,
        )
        st.markdown(f"Assistant: {result.message}")
        st.rerun()


def _render_user_input_panel() -> str | None:
    with st.form("user_message_form", clear_on_submit=True):
        user_message = st.text_input(
            "Message",
            key="user_message_input",
            placeholder="Send a customer service message",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Send", key="send_message")

    if submitted and user_message.strip():
        return user_message.strip()
    return None


def main() -> None:
    st.set_page_config(page_title="Human-in-the-Loop Approval Agent", layout="wide")
    st.title("Human-in-the-Loop Approval Agent")
    st.caption("Customer service assistant with deterministic risk gating and human approval.")

    agent = _init_agent()
    chat_column, human_column = st.columns([2, 1])

    with chat_column:
        st.subheader("Conversation")
        _render_history(agent)
        _render_approval_panel(agent)
        user_message = _render_user_input_panel()

    with human_column:
        st.subheader("Human Interaction")
        _render_human_interaction_panel(agent)

    if user_message:
        response = agent.handle_user_message(user_message)
        assistant_message = agent.get_live_or_cached_assistant_text(user_message, response.message)
        st.markdown(f"Assistant: {assistant_message}")
        st.rerun()


if __name__ == "__main__":
    main()

