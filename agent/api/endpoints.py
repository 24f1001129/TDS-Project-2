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
    return {"message": "Gemini 2.5 Pro Generalist Agent is live."}

@router.get("/health")
def read_health():
    """For the uptime monitor."""
    return {"status": "ok"}

@router.post("/quiz")
async def handle_quiz_request(request: QuizRequest, background_tasks: BackgroundTasks):
    
    if not SECRET_KEY:
        if not os.environ.get("SECRET_KEY"):
             raise HTTPException(status_code=500, detail="Server SECRET_KEY not configured.")
        SECRET_KEY = os.environ.get("SECRET_KEY")
        
    if request.secret != SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid secret.")

    task_data = request.model_dump()

    async def run_with_timeout(data):
        try:
            print(f"[SUPERVISOR] Starting task chain {data.get('url')} with {TASK_TIMEOUT}s timeout.")
            await asyncio.wait_for(solve_quiz_task(data), timeout=TASK_TIMEOUT)
        except asyncio.TimeoutError:
            print(f"[SUPERVISOR] ❌ CRITICAL: Task chain timed out after {TASK_TIMEOUT}s!")

    background_tasks.add_task(run_with_timeout, data=task_data)
    
    return {"status": "Job accepted. Processing in background."}