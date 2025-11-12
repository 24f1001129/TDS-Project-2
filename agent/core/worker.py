import os
import json
import asyncio
from playwright.async_api import async_playwright
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
   - Use this to click on buttons, links, or other elements.
   - Example: {"tool": "click", "selector": "button#submit-button"}

2. {"tool": "fill_text", "selector": "<css_selector>", "text": "<text_to_fill>"}
   - Use this to type into text fields.
   - Example: {"tool": "fill_text", "selector": "input[name='email']", "text": "user@example.com"}

3. {"tool": "task_complete", "summary": "<summary_of_your_findings>"}
   - Use this *only* when the task is fully solved (e.g., you have the answer).
   - The summary will be printed to the logs.

Based on the HTML, decide the *single next step* to solve the task.
The task data is:
"""

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

            for i in range(10):
                print(f"\n[AGENT] --- Loop {i+1} / 10 ---")
                
                print("[AGENT]  👀 Seeing (Scraping page)...")
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
                        print(f"[AGENT]  Executing click({action_json['selector']})...")
                        # TODO: Implement this tool
                    
                    elif action_json["tool"] == "fill_text":
                        print(f"[AGENT]  Executing fill_text({action_json['selector']})...")
                        # TODO: Implement this tool
                    
                    elif action_json["tool"] == "task_complete":
                        print("[AGENT] ✅ Task Complete!")
                        print(f"[AGENT]  Final summary: {action_json['summary']}")
                        break
                    
                    else:
                        print(f"[AGENT] ⚠️ Unknown tool: {action_json['tool']}")

                    await asyncio.sleep(2)

                except Exception as e:
                    print(f"[AGENT] ❌ Error parsing or executing LLM action: {e}")
                    break
            
            await browser.close()
            print("[AGENT]  Browser closed.")

    except Exception as e:
        print(f"[AGENT] ❌ FAILED to process task for {url}")
        print(f"[AGENT] Error: {e}")
    
    finally:
        print("--------------------------------------------------")