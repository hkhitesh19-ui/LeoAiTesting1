import json
from pathlib import Path

STATE_FILE = Path('prototype/outputs/vix_state.json')

def record_vix_context(ctx):
    STATE_FILE.write_text(json.dumps(ctx, indent=2, default=str))
