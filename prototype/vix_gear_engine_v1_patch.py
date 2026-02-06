from prototype.vix_state_recorder_v1 import record_vix_context
from prototype.vix_gear_engine_v1 import select_gear as _select

def select_gear(vix):
    ctx = _select(vix)
    record_vix_context(ctx)
    return ctx
