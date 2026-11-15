import re
from ..rag import retrieve
from ..common import procedure
from ..case_record import log
MAP = {"mri": ["PLAN-2.1", "PLAN-7.1"], "ct": ["PLAN-2.1", "PLAN-7.1"], "tkr": ["PLAN-2.2", "PLAN-7.1"], "arthroscopy": ["PLAN-2.2", "PLAN-7.1"],
       "knee_surgery": ["PLAN-2.2", "PLAN-7.1"], "bariatric": ["PLAN-2.4", "PLAN-7.1"], "chemo": ["PLAN-3.1", "PLAN-7.1"]}
async def _rules(c):
    t = c["raw_request"]; hits = retrieve(t + " " + c["parsed"]["treatment"], "plan_docs")
    p = procedure(t)
    if p == "cosmetic": st, cl, why = "EXCLUDED", ["PLAN-4.1"], "Cosmetic procedure with no functional need is excluded."
    elif p == "experimental": st, cl, why = "EXCLUDED", ["PLAN-4.2"], "Experimental/investigational treatment is excluded."
    elif re.search(r"out-of-network", t, re.I): st, cl, why = "EXCLUDED", ["PLAN-4.3"], "Out-of-network provider is excluded."
    elif p in MAP: st, cl, why = "COVERED_PRIOR_AUTH", MAP[p], "Covered service; prior authorisation required."
    else: st, cl, why = "UNCLEAR", ["PLAN-7.2"], "Could not match a covered service."
    c["coverage_findings"] = {"status": st, "clauses": cl, "reason": why, "retrieved": hits, "confidence": 0.9 if st != "UNCLEAR" else 0.5}
    log(c, "Coverage Retrieval", f"{st}: {', '.join(cl)}")

from .. import llm
SYS = ("You are the Coverage Retrieval agent. Decide ONLY from the PLAN CLAUSES given (retrieved by RAG). Never use outside knowledge. "
       "Check exclusions (cosmetic, experimental, out-of-network) and whether the service is covered / needs prior authorisation. "
       'Return {"status": "COVERED_PRIOR_AUTH" | "EXCLUDED" | "UNCLEAR", "clauses": [clause IDs that support your finding], "reason": str, "confidence": 0-1}. '
       "Use UNCLEAR if the clauses do not settle it. Cite only IDs that appear in the PLAN CLAUSES.")
async def _llm(c):
    hits = retrieve(c["raw_request"] + " " + c["parsed"]["treatment"], "plan_docs", 6)
    r = await llm.ask_json(SYS, f"REQUEST:\n{c['raw_request']}\n\nPLAN CLAUSES:\n" + "\n".join(f"{h['clause_id']}: {h['text']}" for h in hits))
    ids = {h["clause_id"] for h in hits}; cl = [i for i in r["clauses"] if i in ids]
    assert r["status"] in ("COVERED_PRIOR_AUTH", "EXCLUDED", "UNCLEAR") and cl, "invalid or ungrounded output"
    c["coverage_findings"] = {"status": r["status"], "clauses": cl, "reason": r["reason"], "retrieved": hits, "confidence": float(r.get("confidence", .8))}
    log(c, "Coverage Retrieval", f"[LLM] {r['status']}: {', '.join(cl)}")
async def run(c): await llm.with_fallback(c, "Coverage Retrieval", _llm, _rules)
