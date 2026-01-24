from fastapi import FastAPI
from backend.routes.execution_state import router as execution_state_router
from backend.routes.health import router as health_router

app = FastAPI()

app.include_router(health_router)
app.include_router(execution_state_router)
