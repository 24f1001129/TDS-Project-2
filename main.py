import os
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from playwright.async_api import async_playwright

app = FastAPI()
SECRET_KEY = os.environ.get("SECRET_KEY")

class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str

async def solve_quiz_task(url: str, email: str, secret: str):
    """
    This is our asynchronous worker.
    It now uses Playwright to scrape the target URL.
    """
    
    print("--------------------------------------------------")
    print(f"[WORKER] 🤖 Task accepted for URL: {url}")
    
    try:
        async with async_playwright() as p:
            print("[WORKER]  launching browser...")
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            print(f"[WORKER]  navigating to {url}...")
            await page.goto(url)
            await asyncio.sleep(2) 
            
            print("[WORKER] 📸 Scraping page content...")
            content = await page.content()
            
            print("[WORKER] ✅ Successfully scraped page.")
            print("\n--- Start of Scraped Content (first 1000 chars) ---")
            print(content[:1000])
            print("--- End of Scraped Content ---")
            
            await browser.close()

    except Exception as e:
        print(f"[WORKER] ❌ FAILED to process task for {url}")
        print(f"[WORKER] Error: {e}")
    
    finally:
        print("--------------------------------------------------")

@app.get("/")
def read_root():
    return {"message": "Hello World. LLM Analysis Quiz agent is standing by."}

@app.get("/health")
def read_health():
    return {"status": "ok"}

@app.post("/quiz")
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