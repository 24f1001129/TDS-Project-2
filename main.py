from fastapi import FastAPI
from agent.api.endpoints import router as api_router

app = FastAPI(title="LLM Router Agent")

app.include_router(api_router)