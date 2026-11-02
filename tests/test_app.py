from streamlit.testing.v1 import AppTest


def test_app_renders_and_executes_safe_action():
    at = AppTest.from_file("../app.py").run()

    at.text_input(key="user_message_input").set_value("lookup order 1001")
    at.form_submit_button(key="send_message").click().run()

    messages = [m.value for m in at.markdown if "Assistant:" in m.value]
    assert any("Order 1001" in msg for msg in messages)


def test_app_shows_approval_ui_for_high_risk_refund():
    at = AppTest.from_file("../app.py").run()

    at.text_input(key="user_message_input").set_value("refund order 1001 amount 500")
    at.form_submit_button(key="send_message").click().run()

    assert any("Approval required" in m.value for m in at.markdown)


def test_app_shows_right_side_human_panel_and_handles_external_resolution():
    at = AppTest.from_file("../app.py").run()

    at.text_input(key="user_message_input").set_value("human please")
    at.form_submit_button(key="send_message").click().run()

    at.selectbox(key="human_outcome").set_value("handled_externally").run()
    at.text_input(key="human_operator_id").set_value("ops-user-1").run()
    at.text_area(key="human_notes").set_value("Solved via phone").run()
    at.button(key="human_submit").click().run()

    assert any("handled externally" in m.value.lower() for m in at.markdown)

