try:
    from ..case_record import log
except (ImportError, ValueError):
    from case_record import log
def _template(c):
    p, d = c["parsed"], c["decision"]
    cites = "\n".join(f"  - {i}: {c['clause_text'].get(i, '')}" for i in c["cited_clauses"])
    body = {"APPROVE": f"We are pleased to confirm that pre-authorisation for {p['treatment']} has been APPROVED.",
            "DENY": f"After clinical and benefit review, pre-authorisation for {p['treatment']} has been DENIED. This decision was reviewed by a human peer reviewer.",
            "MORE_INFO": f"We need additional information before deciding on {p['treatment']}. Please send the missing clinical documentation."}[d]
    return (f"Re: Pre-authorisation request, patient {p.get('patient') or 'N/A'} (Case {c['case_id']})\nProvider: {p.get('provider')}\n\nDear Provider,\n\n{body}\n\n"
            f"Basis for this decision:\n{cites}\n\nYou may appeal this decision or resubmit with further documentation.\n\nSincerely,\nSynthCare Utilisation Management")
try:
    from .. import llm
except (ImportError, ValueError):
    import llm
SYS = ("You are the Letter Drafter agent for a health insurer. Write a professional pre-authorisation response letter that matches the FINAL DECISION exactly "
       "(approval / denial / request for more information). Cite every clause ID provided with its text. Do not add clauses, facts or promises not provided. "
       "For a denial, mention the human peer review and the right to appeal. Plain text, under 250 words.")
async def _llm(c):
    cites = "\n".join(f"{i}: {c['clause_text'].get(i, '')}" for i in c["cited_clauses"])
    c["letter"] = await llm.ask_text(SYS, f"FINAL DECISION: {c['decision']}\nCASE: {c['case_id']}\nPARSED: {c['parsed']}\nHUMAN REVIEW: {c['human_review']}\nCLAUSES:\n{cites}")
    log(c, "Letter Drafter", f"[LLM] Drafted {c['decision']} letter")
async def _rules(c):
    c["letter"] = _template(c); log(c, "Letter Drafter", f"Drafted {c['decision']} letter")
async def run(c): await llm.with_fallback(c, "Letter Drafter", _llm, _rules)
