from prototype.vix_contracts import VixContext
from prototype.vix_state_recorder_v1 import record_vix_context
from datetime import datetime

def select_gear_from_vix(vix):
    if vix < 13:
        ctx = VixContext(
            vix=vix,
            gear='RATIO_SPREAD',
            reason='Low VIX < 13 → Gamma expansion',
            ts=datetime.utcnow().isoformat() + 'Z'
        )
    elif vix <= 18:
        ctx = VixContext(
            vix=vix,
            gear='SAFE_FUTURE',
            reason='Mid VIX 13–18 → Trend with hedge',
            ts=datetime.utcnow().isoformat() + 'Z'
        )
    else:
        ctx = VixContext(
            vix=vix,
            gear='BULL_CALL_SPREAD',
            reason='High VIX > 18 → Sell IV',
            ts=datetime.utcnow().isoformat() + 'Z'
        )

    record_vix_context(ctx)
    return ctx
