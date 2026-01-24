from fastapi import APIRouter
from prototype.execution_state_endpoint_v1 import get_execution_state

router = APIRouter()

@router.get('/execution_state')
def execution_state():
    return get_execution_state()
