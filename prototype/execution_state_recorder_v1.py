from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json

STATE_FILE = Path(__file__).parent / "outputs" / "execution_state.json"

@dataclass
class ExecutionState:
    status: str          # WAIT / EXECUTE
    gear: str | None
    reason: str
    ts: str

def record_execution_state(status: str, gear: str | None, reason: str) -> ExecutionState:
    state = ExecutionState(
        status=status,
        gear=gear,
        reason=reason,
        ts=datetime.now(timezone.utc).isoformat()
    )
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(asdict(state), indent=2))
    return state

def load_execution_state() -> ExecutionState | None:
    if not STATE_FILE.exists():
        return None
    data = json.loads(STATE_FILE.read_text())
    return ExecutionState(**data)
