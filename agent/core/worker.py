import os
import asyncio
from playwright.async_api import async_playwright
from openai import AsyncOpenAI

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

llm_client = AsyncOpenAI(
    api_key=os.environ.get("AIPIPE_API_KEY"),
    base_url=os.environ.get("AIPIPE_BASE_URL"),
)

SYSTEM_PROMPT = """
You are a highly intelligent data analysis agent.
Your goal is to understand and solve a data quiz.
You will be given the raw HTML of a quiz page.
Analyze the HTML and, in plain English, state:
1. What is the task or question?
2. What are the steps to solve it?
3. What is the final submission URL?
"""

async def solve_quiz_task(url: str, email: str, secret: str):
    """
    This worker now scrapes the page AND calls an LLM to understand it.
    """
    
    print("--------------------------------------------------")
    print(f"[WORKER] 🤖 Task accepted for URL: {url}")
    
    try:
        async with async_playwright() as p:
            print("[WORKER]  Launching browser...")
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            page = await browser.new_page(user_agent=USER_AGENT)
            
            print(f"[WORKER]  Navigating to {url}...")
            await page.goto(url)
            await page.wait_for_load_state("networkidle", timeout=5000)
            
            print("[WORKER] 📸 Scraping page content...")
            scraped_html = await page.content()
            await browser.close()
            
            print(f"[WORKER] ✅ Successfully scraped page ({len(scraped_html)} bytes).")

        print("[WORKER] 🧠 Connecting to LLM to understand the task...")
        
        response = await llm_client.chat.completions.create(
            model="gpt-4o", 
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": scraped_html}
            ]
        )
        
        llm_response = response.choices[0].message.content
        
        print("[WORKER] ✅ LLM analysis complete.")
        print("\n--- LLM Response ---")
        print(llm_response)

    except Exception as e:
        print(f"[WORKER] ❌ FAILED to process task for {url}")
        print(f"[WORKER] Error: {e}")
    
    finally:
        print("--------------------------------------------------")