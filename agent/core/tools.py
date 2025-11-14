import asyncio

async def tool_click(page, selector: str):
    print(f"[TOOL_STUB] 🦾 CLICK: {selector}")
    await asyncio.sleep(0.5)
    return f"Clicked element '{selector}'."

async def tool_fill_text(page, selector: str, text: str):
    print(f"[TOOL_STUB] 🦾 FILL: {selector} with '{text}'")
    await asyncio.sleep(0.5)
    return f"Filled '{selector}'."

async def tool_call_api(url: str, headers: dict = None):
    print(f"[TOOL_STUB] 📡 API CALL: {url}")
    await asyncio.sleep(1)
    return "{'api_response': 'dummy_data'}"

async def tool_read_file(url: str):
    print(f"[TOOL_STUB] 📂 READ FILE: {url}")
    await asyncio.sleep(1)
    return "Dummy PDF text: 'value = 123'"

async def tool_run_python_code(code: str):
    print(f"[TOOL_STUB] 🐍 RUN PYTHON: {code}")
    await asyncio.sleep(2)
    return "Python output: 123.45"

async def tool_submit_answer(submission_url: str, answer_json: dict):
    print(f"[TOOL_STUB] 📤 SUBMIT: {answer_json} to {submission_url}")
    await asyncio.sleep(1)
    return "Task completed. Final answer submitted."