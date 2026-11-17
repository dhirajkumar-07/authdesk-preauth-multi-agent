import re
try:
    from ..rag import retrieve
except (ImportError, ValueError):
    from rag import retrieve
try:
    from ..common import procedure, MISSING
except (ImportError, ValueError):
    from common import procedure, MISSING
try:
    from ..case_record import log
except (ImportError, ValueError):
    from case_record import log
async def _rules(c):
    t = c["raw_request"]; tl = t.lower(); p = procedure(t); hits = retrieve(t, "guidelines")
    st, cl, why = "MET", [], ""
    if re.search(MISSING, tl):
        st = "INSUFFICIENT"; cl = {"knee_surgery": ["GL-KNEE-2.1"], "ct": ["GL-CT-8.1"]}.get(p, [h["clause_id"] for h in hits[:1]])
        why = "Clinical documentation is missing, so criteria cannot be assessed."
    elif p == "mri":
        weeks = max([int(x) for x in re.findall(r"(\d+)\s*weeks?", tl)] or [0]); noflag = re.search(r"\bno\b[^.]*red[- ]flag", tl)
        if weeks >= 6 or (not noflag and re.search(r"neurolog|deficit", tl)): cl, why = ["GL-MRI-3.1"], "Pain persisted 6+ weeks or red flags present."
        else: st, cl, why = "NOT_MET", ["GL-MRI-3.2"], "Acute pain under 6 weeks with no red flags: MRI not indicated."
    elif p == "tkr":
        ok = "severe" in tl and re.search(r"\b([3-9]|\d{2})\s*months", tl)
        cl = ["GL-TKR-4.1"]; why = "Severe OA with 3+ months failed conservative care." if ok else "Criteria for TKR not met."; st = "MET" if ok else "NOT_MET"
    elif p == "arthroscopy":
        bad = "degenerative" in tl and "no meniscal" in tl
        cl = ["GL-KNEE-2.1"]; st = "NOT_MET" if bad else "MET"; why = "Degenerative OA alone is not an indication." if bad else "Meniscal tear with mechanical symptoms."
    elif p == "chemo":
        ok = "confirmed" in tl and "treatment plan" in tl
        cl = ["GL-ONC-6.1"]; st = "MET" if ok else "INSUFFICIENT"; why = "Confirmed diagnosis and oncologist plan present." if ok else "Needs confirmed diagnosis and plan."
    elif p == "bariatric":
        m = re.search(r"bmi\s*(\d+)", tl); ok = bool(m) and int(m.group(1)) >= 40 and "diet" in tl
        cl = ["GL-BAR-5.1"]; st = "MET" if ok else "NOT_MET"; why = "BMI 40+ with supervised diet attempts." if ok else "BMI/diet criteria not met."
    elif p in ("cosmetic", "experimental"): st, why = "NOT_APPLICABLE", "Excluded by plan; no clinical review needed."
    else: st, cl, why = "INSUFFICIENT", [h["clause_id"] for h in hits[:1]], "No matching guideline."
    c["necessity_findings"] = {"status": st, "clauses": cl, "reason": why, "retrieved": hits, "confidence": 0.85 if st != "INSUFFICIENT" else 0.6}
    log(c, "Medical Necessity", f"{st}: {', '.join(cl) or '-'}")

try:
    from .. import llm
except (ImportError, ValueError):
    import llm
SYS = ("You are the Medical Necessity agent. Judge ONLY against the GUIDELINE CLAUSES given (retrieved by RAG). Never use outside medical knowledge. "
       "If the request lacks the documentation needed to apply the criteria, the status is INSUFFICIENT. If the treatment is excluded by the plan (cosmetic/experimental) use NOT_APPLICABLE with clauses []. "
       'Return {"status": "MET" | "NOT_MET" | "INSUFFICIENT" | "NOT_APPLICABLE", "clauses": [guideline IDs used], "reason": str, "confidence": 0-1}. Cite only IDs in the GUIDELINE CLAUSES.')
async def _llm(c):
    hits = retrieve(c["raw_request"], "guidelines", 5)
    r = await llm.ask_json(SYS, f"REQUEST:\n{c['raw_request']}\n\nGUIDELINE CLAUSES:\n" + "\n".join(f"{h['clause_id']}: {h['text']}" for h in hits))
    ids = {h["clause_id"] for h in hits}; cl = [i for i in r["clauses"] if i in ids]
    assert r["status"] in ("MET", "NOT_MET", "INSUFFICIENT", "NOT_APPLICABLE"), "invalid status"
    assert cl or r["status"] == "NOT_APPLICABLE", "ungrounded output"
    c["necessity_findings"] = {"status": r["status"], "clauses": cl, "reason": r["reason"], "retrieved": hits, "confidence": float(r.get("confidence", .8))}
    log(c, "Medical Necessity", f"[LLM] {r['status']}: {', '.join(cl) or '-'}")
async def run(c): await llm.with_fallback(c, "Medical Necessity", _llm, _rules)
