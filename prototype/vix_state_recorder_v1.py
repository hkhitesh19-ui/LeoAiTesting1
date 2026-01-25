import json
from pathlib import Path
from prototype.vix_contracts import VixContext

STATE_FILE = Path('prototype/outputs/vix_state.json')

def record_vix_context(ctx: VixContext):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(ctx.__dict__, indent=2))

def load_last_vix_context():
    if not STATE_FILE.exists():
        return None
    return json.loads(STATE_FILE.read_text())
