"""LLM Client with Microsoft Semantic Kernel integration and deterministic offline rule fallback."""
import os
import json
import re
from typing import Dict, Any, Callable, Awaitable
from dotenv import load_dotenv

load_dotenv()

def provider() -> str:
    if os.getenv("FORCE_RULES") == "1":
        return None
    key = os.getenv("GEMINI_API_KEY", "")
    if key and key.startswith("AIzaSy"):
        return "gemini"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return None

def is_llm_available() -> bool:
    return provider() is not None

def get_model_name() -> str:
    p = provider()
    if p == "gemini":
        return os.getenv("LLM_MODEL", "gemini-2.0-flash")
    if p == "openai":
        return os.getenv("LLM_MODEL", "gpt-4o-mini")
    return "Rule-Based Engine (Offline)"

_sk_kernel = None
_sk_chat = None

def get_chat_service():
    global _sk_kernel, _sk_chat
    if _sk_chat is not None:
        return _sk_chat
    p = provider()
    if p == "gemini":
        from semantic_kernel import Kernel
        from semantic_kernel.connectors.ai.google.google_ai import GoogleAIChatCompletion, GoogleAIChatPromptExecutionSettings
        _sk_kernel = Kernel()
        _sk_chat = GoogleAIChatCompletion(
            gemini_model_id=get_model_name(),
            api_key=os.environ["GEMINI_API_KEY"]
        )
        return _sk_chat
    elif p == "openai":
        from semantic_kernel import Kernel
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
        _sk_kernel = Kernel()
        _sk_chat = OpenAIChatCompletion(
            ai_model_id=get_model_name(),
            api_key=os.environ["OPENAI_API_KEY"]
        )
        return _sk_chat
    return None

async def ask_text(system_prompt: str, user_content: str) -> str:
    svc = get_chat_service()
    if not svc:
        raise RuntimeError("No LLM service configured.")
    from semantic_kernel.contents import ChatHistory
    h = ChatHistory()
    h.add_system_message(system_prompt)
    h.add_user_message(user_content)
    res = await asyncio.wait_for(svc.get_chat_message_content(chat_history=h), timeout=3.5)
    return str(res).strip()

async def ask_json(system_prompt: str, user_content: str) -> Dict[str, Any]:
    prompt = system_prompt + "\nReturn ONLY a single valid JSON object. No markdown fences, no explanation."
    txt = await ask_text(prompt, user_content)
    m = re.search(r"\{.*\}", txt, re.DOTALL)
    if not m:
        raise ValueError(f"No JSON object found in response: {txt[:100]}")
    return json.loads(m.group(0))

async def with_fallback(
    agent_name: str,
    llm_func: Callable[[Any], Awaitable[Any]],
    rule_func: Callable[[Any], Any],
    case_record: Any
) -> Any:
    """Execute LLM agent function if available, otherwise seamlessly execute rule fallback."""
    if is_llm_available():
        try:
            return await llm_func(case_record)
        except Exception as e:
            # Fall back to rules on any rate limit, quota, or network exception
            res = rule_func(case_record)
            return res
    else:
        return rule_func(case_record)

