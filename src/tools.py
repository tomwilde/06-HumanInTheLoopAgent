from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(slots=True)
class ToolSpec:
    name: str
    risk_level: str
    sensitive: bool
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, tool: ToolSpec) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolSpec:
        return self._tools[name]

    def execute(self, name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        return self.get(name).handler(parameters)

    def has(self, name: str) -> bool:
        return name in self._tools


def _lookup_order(params: dict[str, Any]) -> dict[str, Any]:
    order_id = str(params["order_id"])
    return {
        "order_id": order_id,
        "status": "shipped",
        "summary": f"Order {order_id} is currently shipped.",
    }


def _faq_retrieval(params: dict[str, Any]) -> dict[str, Any]:
    topic = str(params.get("topic", "general"))
    return {
        "topic": topic,
        "summary": f"FAQ answer for {topic}: Please allow 3-5 business days for processing.",
    }


def _issue_refund(params: dict[str, Any]) -> dict[str, Any]:
    amount = float(params["amount"])
    return {
        "order_id": str(params["order_id"]),
        "amount": amount,
        "summary": f"Refund issued for order {params['order_id']} amount {amount:.2f}.",
    }


def _account_change(params: dict[str, Any]) -> dict[str, Any]:
    field = str(params.get("field", "unknown"))
    value = str(params.get("value", ""))
    return {"field": field, "value": value, "summary": f"Updated account {field} to {value}."}


def _send_email(params: dict[str, Any]) -> dict[str, Any]:
    return {"summary": f"Email queued to {params.get('to', 'unknown@example.com')}"}


def _spend_money(params: dict[str, Any]) -> dict[str, Any]:
    amount = float(params.get("amount", 0))
    return {"amount": amount, "summary": f"Spent {amount:.2f} credits."}


def _delete_record(params: dict[str, Any]) -> dict[str, Any]:
    record_id = str(params.get("record_id", "unknown"))
    return {"record_id": record_id, "summary": f"Record {record_id} deleted."}


def _escalate_to_human(params: dict[str, Any]) -> dict[str, Any]:
    queue_path = Path(params["queue_path"])
    payload = params["payload"]
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with queue_path.open("a", encoding="utf-8") as output_file:
        output_file.write(json.dumps(payload) + "\n")
    return {"summary": "Escalated to human queue.", "handoff_target": "human_queue"}


def build_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ToolSpec("lookup_order", "low", False, _lookup_order))
    registry.register(ToolSpec("faq_retrieval", "low", False, _faq_retrieval))
    registry.register(ToolSpec("issue_refund", "high", False, _issue_refund))
    registry.register(ToolSpec("account_change", "high", False, _account_change))
    registry.register(ToolSpec("send_email", "high", True, _send_email))
    registry.register(ToolSpec("spend_money", "high", True, _spend_money))
    registry.register(ToolSpec("delete_record", "high", True, _delete_record))
    registry.register(ToolSpec("escalate_to_human", "high", True, _escalate_to_human))
    return registry

