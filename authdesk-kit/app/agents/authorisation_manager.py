from ..rag import clause_text
from ..case_record import log
async def _rules(c):
    cov, nec = c["coverage_findings"], c["necessity_findings"]
    if cov["status"] == "EXCLUDED": d, cl, conf = "DENY", cov["clauses"], 0.93
    elif nec["status"] == "INSUFFICIENT": d, cl, conf = "MORE_INFO", ["PLAN-7.2"] + nec["clauses"], 0.7
    elif nec["status"] == "NOT_MET": d, cl, conf = "DENY", cov["clauses"] + nec["clauses"], 0.88
    elif cov["status"] == "UNCLEAR": d, cl, conf = "MORE_INFO", ["PLAN-7.2"] + nec["clauses"], 0.6
    else: d, cl, conf = "APPROVE", cov["clauses"] + nec["clauses"], round(min(cov["confidence"], nec["confidence"]) + 0.05, 2)
    cl = list(dict.fromkeys(cl))
    c.update(decision=d, ai_decision=d, confidence=conf, cited_clauses=cl, clause_text={i: clause_text(i) for i in cl})
    log(c, "Authorisation Manager", f"{d} (confidence {conf}) citing {', '.join(cl)}")

from .. import llm
SYS = ("You are the Authorisation Manager. Combine the Coverage and Medical Necessity findings into ONE decision. Rules: plan EXCLUDED -> DENY; "
       "medical criteria NOT_MET -> DENY; documentation INSUFFICIENT or coverage UNCLEAR -> MORE_INFO (cite PLAN-7.2); both fine -> APPROVE. "
       'Return {"decision": "APPROVE"|"DENY"|"MORE_INFO", "cited_clauses": [IDs taken ONLY from the findings, plus PLAN-7.2 for MORE_INFO], "confidence": 0-1, "rationale": str}.')
async def _llm(c):
    cov, nec = c["coverage_findings"], c["necessity_findings"]
    pick = lambda f: {k: f[k] for k in ("status", "clauses", "reason")}
    r = await llm.ask_json(SYS, f"REQUEST:\n{c['raw_request']}\n\nCOVERAGE: {pick(cov)}\nNECESSITY: {pick(nec)}")
    allowed = set(cov["clauses"]) | set(nec["clauses"]) | {"PLAN-7.2"}
    cl = list(dict.fromkeys(i for i in r["cited_clauses"] if i in allowed))
    assert r["decision"] in ("APPROVE", "DENY", "MORE_INFO") and cl, "invalid decision"
    c.update(decision=r["decision"], ai_decision=r["decision"], confidence=float(r.get("confidence", .8)), cited_clauses=cl, clause_text={i: clause_text(i) for i in cl})
    c["rationale"] = r.get("rationale", "")
    log(c, "Authorisation Manager", f"[LLM] {r['decision']} (confidence {c['confidence']}) citing {', '.join(cl)}")
async def run(c): await llm.with_fallback(c, "Authorisation Manager", _llm, _rules)
