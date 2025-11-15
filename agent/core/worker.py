# agent/core/worker.py
import os
import json
import asyncio
import re
import traceback  # NEW IMPORT for detailed error logging
from playwright.async_api import async_playwright, Page
from openai import AsyncOpenAI
from agent.core.tools import *

# --- 1. Client Configuration ---
llm_client = AsyncOpenAI(
    api_key=os.environ.get("AIPIPE_API_KEY"),
    base_url=os.environ.get("AIPIPE_BASE_URL"),
)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

# --- 2. HTML Cleaner ---
def clean_html_for_router(html: str) -> str:
    html = re.sub(r'<(script|style).*?>.*?</\1>', '', html, flags=re.DOTALL)
    html = re.sub(r'<svg.*?>.*?</svg>', '', html, flags=re.DOTALL)
    html = re.sub(r'', '', html, flags=re.DOTALL)
    html = re.sub(r'<.*?>', ' ', html)
    html = re.sub(r'\s+', ' ', html).strip()
    return html

# --- 3. Specialist Prompts ---
# (Prompts are unchanged)
ROUTER_PROMPT_TEMPLATE = """... (omitted for brevity) ..."""
SIMPLE_AGENT_PROMPT = """... (omitted for brevity) ..."""
CODE_AGENT_PROMPT = """... (omitted for brevity) ..."""
PRO_AGENT_PROMPT = """... (omitted for brevity) ..."""

# --- 4. The Specialist Agent Loops (NEW ERROR LOGGING) ---

async def run_agent_loop(agent_name: str, model_name: str, system_prompt: str,
                         page: Page, task_data: dict, initial_html: str):
    # ... (function definition and 'Think' loop are unchanged) ...
    
    task_hint = task_data.get("task_hint", "Solve the task.")
    formatted_prompt = system_prompt.format(task_hint=task_hint, html_content=initial_html)
    message_history = [
        {"role": "system", "content": "You must respond with a single valid JSON tool command."},
        {"role": "user", "content": formatted_prompt}
    ]
    
    for i in range(10):
        print(f"\n[{agent_name}] --- Loop {i+1} / 10 ---")
        
        # 1. THINK
        print(f"[{agent_name}]  🧠 Thinking (Calling {model_name})...")
        try:
            response = await llm_client.chat.completions.create(
                model=model_name,
                messages=message_history,
                response_format={"type": "json_object"}
            )
            llm_response_text = response.choices[0].message.content
            print(f"[{agent_name}]  LLM response: {llm_response_text}")
            message_history.append({"role": "assistant", "content": llm_response_text})
        except Exception as e:
            print(f"[{agent_name}] ❌ LLM call failed:")
            print(traceback.format_exc()) # DETAILED LOGGING
            message_history.append({"role": "user", "content": f"LLM Error: {e}. Please try again."})
            continue

        # 2. ACT
        try:
            try:
                action_json = json.loads(llm_response_text)
            except json.JSONDecodeError:
                raise ValueError(f"LLM returned invalid JSON: {llm_response_text}")

            tool = action_json.get("tool") # Safe .get()
            result = f"Error: Unknown tool '{tool}'."

            if tool == "click":
                result = await tool_click(page, action_json.get("selector"))
            # ... (all other tool 'elif' blocks) ...
            elif tool == "fill_text":
                result = await tool_fill_text(page, action_json.get("selector"), action_json.get("text"))
            elif tool == "call_api":
                result = await tool_call_api(action_json.get("url"), action_json.get("headers"))
            elif tool == "read_file":
                result = await tool_read_file(action_json.get("url"))
            elif tool == "run_python_code":
                result = await tool_run_python_code(action_json.get("code"))
            elif tool == "take_screenshot_and_analyze":
                result = await tool_take_screenshot_and_analyze(page, action_json.get("analysis_prompt"))
            elif tool == "submit_answer":
                result = await tool_submit_answer(action_json.get("submission_url"), action_json.get("answer_json"))
                print(f"[{agent_name}] ✅ Task Complete!")
                return result
            else:
                result = f"Error: LLM returned an unknown tool: '{tool}'."

            # 3. SEE (Update context for next loop)
            print(f"[{agent_name}]  Tool output: {result[:500]}...")
            await page.wait_for_load_state("networkidle", timeout=3000)
            new_html = await page.content()
            
            message_history.append({"role": "user", "content": f"Tool Output: {result}\n\nNew Page HTML:\n{new_html}"})

        except Exception as e:
            # --- THIS IS THE NEW, DETAILED LOGGING ---
            print(f"[{agent_name}] ❌ Error in agent loop (ACT phase):")
            print(traceback.format_exc()) # Print the full stack trace
            # --- END NEW LOGGING ---
            message_history.append({"role": "user", "content": f"Error: {e}. Please try again."})
            
    return f"{agent_name} finished (max loops reached)."

# --- 5. The Router Function (Unchanged) ---
async def decide_specialist(task_data, raw_html: str):
    # ... (code is unchanged) ...
    print("[ROUTER] 🧠 Deciding which specialist to use...")
    print("[ROUTER]  Cleaning HTML for analysis...")
    cleaned_html = clean_html_for_router(raw_html)
    prompt = ROUTER_PROMPT_TEMPLATE.format(
        task_data=json.dumps(task_data, indent=2),
        cleaned_html_snippet=cleaned_html[:5000]
    )
    try:
        response = await llm_client.chat.completions.create(
            model="openai/gpt-5-image-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        choice = response.choices[0].message.content.strip().upper()
        print(f"[ROUTER]  LLM choice: {choice}")
        if "CODE" in choice: return "CODE"
        if "PRO" in choice: return "PRO"
        return "SIMPLE"
    except Exception as e:
        print(f"[ROUTER] ❌ Error in router LLM, defaulting to CODE (safer): {e}")
        return "CODE"

# --- 6. The Main Task Entrypoint (NEW ERROR LOGGING) ---
async def solve_quiz_task(task_data: dict):
    url = task_data.get("url")
    if not url:
        print("[AGENT] ❌ FAILED: No 'url' field in task_data.")
        return

    print(f"[AGENT] 🤖 New task accepted for URL: {url}")
    try:
        async with async_playwright() as p:
            # ... (browser launch, goto, scrape... all unchanged) ...
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            page = await browser.new_page(user_agent=USER_AGENT)
            print(f"[AGENT]  Navigating to {url}...")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            html_content = await page.content()
            print("[AGENT]  Page content scraped.")
            
            specialist = await decide_specialist(task_data, html_content)
            print(f"[ROUTER]  Decision: Routing to {specialist}_AGENT.")
            
            if specialist == "CODE":
                result = await run_agent_loop("CODE_AGENT", "openai/gpt-5-pro", CODE_AGENT_PROMPT, page, task_data, html_content)
            elif specialist == "PRO":
                result = await run_agent_loop("PRO_AGENT", "openai/gpt-5-pro", PRO_AGENT_PROMPT, page, task_data, html_content)
            else:
                result = await run_agent_loop("SIMPLE_AGENT", "openai/gpt-5-image-mini", SIMPLE_AGENT_PROMPT, page, task_data, html_content)
            
            print(f"[AGENT]  Specialist finished with result: {result}")
            await browser.close()
            
    except Exception as e:
        # --- THIS IS THE NEW, DETAILED LOGGING ---
        print(f"[AGENT] ❌ CRITICAL FAILURE in task:")
        print(traceback.format_exc()) # Print the full stack trace
        # --- END NEW LOGGING ---
    finally:
        print(f"--------------------------------------------------")