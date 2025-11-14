import os
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from agent.models.schemas import QuizRequest
from agent.core.worker import solve_quiz_task

router = APIRouter()
SECRET_KEY = os.environ.get("SECRET_KEY")
TASK_TIMEOUT = 170.0

@router.get("/")
def read_root():
    return {"message": "Hello World. LLM Router agent is standing by."}

@router.get("/health")
def read_health():
    return {"status": "ok"}

@router.post("/quiz")
async def handle_quiz_request(request: QuizRequest, background_tasks: BackgroundTasks):
    
    if not SECRET_KEY:
        raise HTTPException(status_code=500, detail="Server not configured.")

    if request.secret != SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid secret.")

    task_data = request.model_dump()
    async def run_with_timeout(data):
        try:
            print(f"[SUPERVISOR] Starting task {data.get('url')} with {TASK_TIMEOUT}s timeout.")
            await asyncio.wait_for(solve_quiz_task(data), timeout=TASK_TIMEOUT)
        except asyncio.TimeoutError:
            print(f"[SUPERVISOR] CRITICAL: Task timed out after {TASK_TIMEOUT}s!")

    background_tasks.add_task(run_with_timeout, data=task_data)
    
    return {"status": "Job accepted and processing in background."}