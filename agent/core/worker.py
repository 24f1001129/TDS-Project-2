import asyncio
from playwright.async_api import async_playwright

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
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
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
            # -------------------------
            
            await browser.close()

    except Exception as e:
        print(f"[WORKER] ❌ FAILED to process task for {url}")
        print(f"[WORKER] Error: {e}")
    
    finally:
        print("--------------------------------------------------")