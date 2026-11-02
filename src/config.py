from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class AppConfig:
    confidence_threshold: float = 0.75
    refund_limit: float = 100.0
    sensitive_capabilities: set[str] = field(
        default_factory=lambda: {"send_email", "spend_money", "delete_record"}
    )
    human_available: bool = True
    audit_log_path: Path = Path("logs/audit.jsonl")
    handoff_queue_path: Path = Path("logs/handoff_queue.jsonl")
    enable_hash_chain: bool = False
    use_live_llm: bool = False
    openrouter_model: str = "openai/gpt-4.1-mini"

    @classmethod
    def from_env(cls) -> "AppConfig":
        sensitive_csv = os.getenv("SENSITIVE_CAPABILITIES", "send_email,spend_money,delete_record")
        sensitive = {cap.strip() for cap in sensitive_csv.split(",") if cap.strip()}
        return cls(
            confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", "0.75")),
            refund_limit=float(os.getenv("REFUND_LIMIT", "100")),
            sensitive_capabilities=sensitive,
            human_available=_parse_bool(os.getenv("HUMAN_AVAILABLE"), True),
            audit_log_path=Path(os.getenv("AUDIT_LOG_PATH", "logs/audit.jsonl")),
            handoff_queue_path=Path(os.getenv("HANDOFF_QUEUE_PATH", "logs/handoff_queue.jsonl")),
            enable_hash_chain=_parse_bool(os.getenv("ENABLE_HASH_CHAIN"), False),
            use_live_llm=_parse_bool(os.getenv("USE_LIVE_LLM"), False),
            openrouter_model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1-mini"),
        )

