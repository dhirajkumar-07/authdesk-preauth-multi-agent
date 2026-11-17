"""Semantic Kernel LLM layer. Set GEMINI_API_KEY (free, aistudio.google.com) or OPENAI_API_KEY in .env.
No key (or FORCE_RULES=1) -> agents fall back to the built-in rule engine so the demo never breaks."""
import os, json, re, asyncio
try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError: pass
from .case_record import log

def provider():
    if os.getenv("FORCE_RULES") == "1":
        return None
    key = os.getenv("GEMINI_API_KEY", "")
    if key and (key.startswith("AIzaSy") or len(key) > 20):
        return "gemini"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return None

def available():
    return provider() is not None

def mode():
    m = MODEL()
    if available():
        return {"mode": "Google Gemini (Semantic Kernel)", "provider": "gemini", "model": m}
    else:
        return {"mode": "Deterministic ChromaDB (Offline Grounding)", "provider": "gemini", "model": m}

def MODEL(): 
    return os.getenv("LLM_MODEL") or "gemini-2.0-flash"

_svc = _cfg = None
def _service():
    global _svc, _cfg
    if _svc: return _svc
    from semantic_kernel import Kernel
    k = Kernel()
    if provider() == "gemini":
        from semantic_kernel.connectors.ai.google.google_ai import GoogleAIChatCompletion, GoogleAIChatPromptExecutionSettings as S
        svc = GoogleAIChatCompletion(gemini_model_id=MODEL(), api_key=os.environ["GEMINI_API_KEY"])
    else:
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, OpenAIChatPromptExecutionSettings as S
        svc = OpenAIChatCompletion(ai_model_id=MODEL(), api_key=os.environ["OPENAI_API_KEY"])
    k.add_service(svc); _svc, _cfg = svc, S(temperature=0.0); return _svc

async def ask_text(system, user, retries=1):
    from semantic_kernel.contents import ChatHistory
    for i in range(retries):
        try:
            h = ChatHistory(); h.add_system_message(system); h.add_user_message(user)
            res = await asyncio.wait_for(_service().get_chat_message_content(chat_history=h, settings=_cfg), timeout=3.5)
            return str(res).strip()
        except Exception as e:
            if i == retries - 1:
                raise
            await asyncio.sleep(0.5)

async def ask_json(system, user):
    t = await ask_text(system + "\nReply with ONE valid JSON object only. No markdown, no commentary.", user)
    m = re.search(r"\{.*\}", t, re.S)
    return json.loads(m.group(0))

async def with_fallback(c, name, llm_fn, rules_fn):
    """LLM first (grounded on retrieved clauses, validated); on any error fall back to rules and say so in the audit log."""
    if available():
        try: return await llm_fn(c)
        except Exception as e: log(c, name, f"LLM failed ({type(e).__name__}: {str(e)[:80]}); used rule fallback")
    await rules_fn(c)
