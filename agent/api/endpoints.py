import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from agent.models.schemas import QuizRequest
from agent.core.worker import solve_quiz_task

router = APIRouter()
SECRET_KEY = os.environ.get("SECRET_KEY")

@router.get("/")
def read_root():
    return {"message": "Hello World. LLM Analysis Quiz agent is standing by."}

@router.get("/health")
def read_health():
    return {"status": "ok"}

@router.post("/quiz")
async def handle_quiz_request(request: QuizRequest, background_tasks: BackgroundTasks):
    
    if not SECRET_KEY:
        raise HTTPException(
            status_code=500, 
            detail="Server is not configured with a SECRET_KEY."
        )

    if request.secret != SECRET_KEY:
        raise HTTPException(
            status_code=403, 
            detail="Invalid secret."
        )

    background_tasks.add_task(
        solve_quiz_task, 
        url=request.url, 
        email=request.email, 
        secret=request.secret
    )
    
    return {"status": "Job accepted and processing in background."}