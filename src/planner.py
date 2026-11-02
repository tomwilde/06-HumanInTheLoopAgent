from __future__ import annotations

import re

from src.config import AppConfig
from src.models import ProposedAction


def _extract_order_id(text: str) -> str:
    match = re.search(r"order\s*(\d+)", text.lower())
    if match:
        return match.group(1)
    digits = re.findall(r"\d+", text)
    return digits[0] if digits else "unknown"


def _extract_amount(text: str) -> float:
    match = re.search(r"amount\s*(\d+(?:\.\d+)?)", text.lower())
    if match:
        return float(match.group(1))
    prices = re.findall(r"\d+(?:\.\d+)?", text)
    return float(prices[-1]) if prices else 0.0


def plan_action(user_message: str, config: AppConfig) -> tuple[ProposedAction | None, bool]:
    text = user_message.lower()

    if "lookup" in text and "order" in text:
        order_id = _extract_order_id(user_message)
        return (
            ProposedAction(
                name="lookup_order",
                parameters={"order_id": order_id},
                confidence=0.95,
                risk_level="low",
                risk_reason="safe_lookup",
            ),
            False,
        )

    if "faq" in text or "policy" in text or "question" in text:
        return (
            ProposedAction(
                name="faq_retrieval",
                parameters={"topic": user_message},
                confidence=0.9,
                risk_level="low",
                risk_reason="safe_faq",
            ),
            False,
        )

    if "refund" in text:
        order_id = _extract_order_id(user_message)
        amount = _extract_amount(user_message)
        risk = "high" if amount > config.refund_limit else "low"
        return (
            ProposedAction(
                name="issue_refund",
                parameters={"order_id": order_id, "amount": amount},
                confidence=0.86,
                risk_level=risk,
                risk_reason="refund_request",
            ),
            False,
        )

    if "change account" in text or "update account" in text:
        return (
            ProposedAction(
                name="account_change",
                parameters={"field": "email", "value": "updated@example.com"},
                confidence=0.78,
                risk_level="high",
                risk_reason="account_change",
            ),
            False,
        )

    if "email" in text:
        return (
            ProposedAction(
                name="send_email",
                parameters={"to": "user@example.com", "body": "Support update"},
                confidence=0.81,
                risk_level="high",
                risk_reason="send_email",
                sensitive_capability="send_email",
            ),
            False,
        )

    if "delete" in text:
        return (
            ProposedAction(
                name="delete_record",
                parameters={"record_id": "record-1"},
                confidence=0.8,
                risk_level="high",
                risk_reason="delete_record",
                sensitive_capability="delete_record",
            ),
            False,
        )

    return None, True

