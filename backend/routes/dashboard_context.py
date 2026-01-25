from fastapi import APIRouter
from prototype.execution_state_recorder_v1 import load_execution_state
from prototype.spot_signal_state_recorder_v1 import load_last_spot_signal
from prototype.vix_state_recorder_v1 import load_last_vix_context

router = APIRouter()

@router.get('/dashboard/context')
def dashboard_context():
    return {
        'execution': load_execution_state(),
        'spot_signal': load_last_spot_signal(),
        'vix': load_last_vix_context()
    }
