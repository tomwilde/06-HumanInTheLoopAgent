from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AuditLogger:
    path: Path
    enable_hash_chain: bool = False
    _last_hash: str = ""

    def append(self, session_id: str, sequence: int, event: str, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record: dict[str, Any] = {
            "session_id": session_id,
            "sequence": sequence,
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
        }
        record.update(payload)
        serialized_body = json.dumps(record, sort_keys=True)

        if self.enable_hash_chain:
            record["prev_hash"] = self._last_hash
            record_hash = hashlib.sha256(
                (self._last_hash + serialized_body).encode("utf-8")
            ).hexdigest()
            record["hash"] = record_hash
            self._last_hash = record_hash
        else:
            record["hash"] = hashlib.sha256(serialized_body.encode("utf-8")).hexdigest()

        with self.path.open("a", encoding="utf-8") as output_file:
            output_file.write(json.dumps(record) + "\n")


def load_session_events(path: Path, session_id: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("session_id") == session_id:
            events.append(row)
    return events

