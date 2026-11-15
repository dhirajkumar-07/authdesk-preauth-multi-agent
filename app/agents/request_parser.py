import re
from ..case_record import log
async def _rules(c):
    t = c["raw_request"]
    g = lambda p: (re.search(p, t, re.I | re.S) or [None, ""])[1].strip(" .")
    treat = g(r"request\s+(.+?)\s+for\b") or t.split(".")[0]
    c["parsed"] = {"patient": g(r"\b(P-\d+)"), "treatment": treat,
                   "diagnosis": g(r"diagnosis:\s*(.+?)(?:\.\s*provider:|provider:|$)"), "provider": g(r"provider:\s*(.+)$")}
    log(c, "Request Parser", f"Structured request: {treat}")

from .. import llm
async def _llm(c):
    r = await llm.ask_json("You are the Request Parser agent for a health insurer. Extract from the pre-authorisation request: "
        '{"patient": str, "treatment": str, "diagnosis": str, "provider": str}. Use "" if absent. Do not invent facts.', c["raw_request"])
    c["parsed"] = {k: str(r.get(k, "")) for k in ("patient", "treatment", "diagnosis", "provider")}
    log(c, "Request Parser", f"[LLM] Structured request: {c['parsed']['treatment']}")
async def run(c): await llm.with_fallback(c, "Request Parser", _llm, _rules)
