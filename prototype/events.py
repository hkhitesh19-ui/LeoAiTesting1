from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

OUTPUT_DIR = os.path.join("prototype", "outputs")
EVENTS_FILE = os.path.join(OUTPUT_DIR, "events.jsonl")


def _ensure_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def event_log(event: str, data: Optional[Dict[str, Any]] = None, trace_id: str = "") -> None:
    """
    Minimal stable JSONL logger.
    This file MUST exist for import hardening.
    """
    _ensure_dir()
    rec = {
        "ts": utc_now_iso(),
        "event": str(event),
        "trace_id": str(trace_id),
        "data": data or {},
    }
    with open(EVENTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
