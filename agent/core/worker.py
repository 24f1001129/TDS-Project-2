import os
import json
import asyncio
from playwright.async_api import async_playwright, Page
from openai import AsyncOpenAI

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

llm_client = AsyncOpenAI(
    api_key=os.environ.get("AIPIPE_API_KEY"),
    base_url=os.environ.get("AIPIPE_BASE_URL"),
)

SYSTEM_PROMPT = """
You are a 'headless' AI agent that controls a web browser.
You will be given the HTML of a webpage and a task.
Your goal is to solve the task.

You have a toolkit of functions. For each step, you MUST respond with a
single JSON object describing the tool you want to use.

Your available tools are:
1. {"tool": "click", "selector": "<css_selector>"}
   - Use this to click on buttons, answer choices, or other elements.
   - Use this for any action that is a "click".
   - Example: {"tool": "click", "selector": "button.qa-quiz-start-button"}

2. {"tool": "fill_text", "selector": "<css_selector>", "text": "<text_to_fill>"}
   - Use this to type into text fields.
   - Example: {"tool": "fill_text", "selector": "input[name='email']", "text": "user@example.com"}

3. {"tool": "task_complete", "summary": "<summary_of_your_findings>"}
   - Use this *only* when the task is fully solved (e.g., you have the final score).
   - The summary will be printed to the logs.

Based on the HTML, decide the *single next step* to solve the task.
The task data is:
"""

async def tool_click(page: Page, selector: str):
    """Uses Playwright to click an element based on its CSS selector."""
    if not selector:
        raise ValueError("No selector provided for click tool")
    print(f"[TOOL]  Clicking element: {selector}")
    await page.locator(selector).first.click()

async def tool_fill_text(page: Page, selector: str, text: str):
    """Uses Playwright to fill a text field."""
    if not selector:
        raise ValueError("No selector provided for fill_text tool")
    if text is None:
        raise ValueError("No text provided for fill_text tool")
    
    print(f"[TOOL]  Filling element '{selector}' with text: '{text}'")
    await page.locator(selector).first.fill(text)

async def solve_quiz_task(task_data: dict):
    
    url = task_data.get("url")
    if not url:
        print("[AGENT] ❌ FAILED: No 'url' field in task_data.")
        return

    print("--------------------------------------------------")
    print(f"[AGENT] 🤖 New task accepted for URL: {url}")
    print(f"[AGENT]  Full task data: {task_data}")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            page = await browser.new_page(user_agent=USER_AGENT)
            
            print(f"[AGENT]  Navigating to {url}...")
            await page.goto(url)
            
            message_history = [
                {
                    "role": "system",
                    "content": f"{SYSTEM_PROMPT}\n{json.dumps(task_data, indent=2)}"
                }
            ]

            for i in range(15):
                print(f"\n[AGENT] --- Loop {i+1} / 15 ---")
                
                print("[AGENT]  👀 Seeing (Scraping page)...")
                await page.wait_for_load_state("networkidle", timeout=3000)
                html_content = await page.content()
                
                message_history.append({"role": "user", "content": html_content})

                print("[AGENT]  🧠 Thinking (Calling LLM)...")
                response = await llm_client.chat.completions.create(
                    model="gpt-4o",
                    messages=message_history,
                    response_format={"type": "json_object"} 
                )
                
                llm_response_text = response.choices[0].message.content
                print(f"[AGENT]  LLM response: {llm_response_text}")
                
                message_history.append({"role": "assistant", "content": llm_response_text})

                try:
                    action_json = json.loads(llm_response_text)
                    
                    if action_json["tool"] == "click":
                        await tool_click(page, action_json.get("selector"))
                    
                    elif action_json["tool"] == "fill_text":
                        await tool_fill_text(page, action_json.get("selector"), action_json.get("text"))
                    
                    elif action_json["tool"] == "task_complete":
                        print("[AGENT] ✅ Task Complete!")
                        print(f"[AGENT]  Final summary: {action_json.get('summary')}")
                        break
                    
                    else:
                        print(f"[AGENT] ⚠️ Unknown tool: {action_json.get('tool')}")

                except Exception as e:
                    print(f"[AGENT] ❌ Error parsing or executing LLM action: {e}")
                    message_history.append({"role": "user", "content": f"Error during action: {e}. Please try again."})

            
            await browser.close()
            print("[AGENT]  Browser closed.")

    except Exception as e:
        print(f"[AGENT] ❌ FAILED to process task for {url}")
        print(f"[AGENT] Error: {e}")
    
    finally:
        print("--------------------------------------------------")