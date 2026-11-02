import pytest
from streamlit.testing.v1 import AppTest


@pytest.mark.acceptance
def test_acceptance_escalation_path_and_fallback_message():
    at = AppTest.from_file("../app.py")
    at.secrets["human_available"] = "false"
    at = at.run()

    at.text_input(key="user_message_input").set_value("manager please")
    at.form_submit_button(key="send_message").click().run()

    assert any("currently unavailable" in m.value.lower() for m in at.markdown)


@pytest.mark.acceptance
def test_acceptance_hitl_edit_and_resume():
    at = AppTest.from_file("../app.py").run()

    at.text_input(key="user_message_input").set_value("refund order 900 amount 120")
    at.form_submit_button(key="send_message").click().run()
    assert any("Approval required" in m.value for m in at.markdown)

    at.text_input(key="edited_params_json").set_value('{"amount": 30.0}').run()
    at.text_input(key="approver_id").set_value("supervisor-1").run()
    at.text_input(key="decision_reason").set_value("within policy").run()
    at.selectbox(key="verdict").set_value("edit_parameters").run()
    at.button(key="submit_decision").click().run()

    assert any("Refund issued" in m.value for m in at.markdown)

