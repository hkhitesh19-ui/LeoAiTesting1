import json
import time
import uuid
from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def new_trace_id():
    return uuid.uuid4().hex[:16]

class EventLogger:
    def __init__(self, path_jsonl: str):
        self.path = path_jsonl

    def log(self, event_type: str, trace_id: str, data: dict):
        payload = {
            "ts": utc_now(),
            "event": event_type,
            "trace_id": trace_id,
            "data": data
        }
        line = json.dumps(payload, ensure_ascii=False)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

def ms():
    return int(time.time() * 1000)
