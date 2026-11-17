"""Fan-out / fan-in orchestration with human routing."""
import asyncio

try:
    from .case_record import STORE, new_case, log, save, record_write
    from .agents import request_parser, coverage_retrieval, medical_necessity, authorisation_manager, letter_drafter
except (ImportError, ValueError):
    from case_record import STORE, new_case, log, save, record_write
    from agents import request_parser, coverage_retrieval, medical_necessity, authorisation_manager, letter_drafter

async def run_case(raw, persist=True):
    c = new_case(raw)
    log(c, "Orchestrator", "Case initiated. Running Request Parser...")
    await request_parser.run(c)
    record_write(c, "parsed", c.get("parsed", {}), "Request Parser")

    log(c, "Orchestrator", "FAN-OUT: Coverage Retrieval and Medical Necessity in parallel")
    await asyncio.gather(coverage_retrieval.run(c), medical_necessity.run(c))
    record_write(c, "coverage_findings", c.get("coverage_findings", {}), "Coverage Retrieval")
    record_write(c, "necessity_findings", c.get("necessity_findings", {}), "Medical Necessity")

    log(c, "Orchestrator", "FAN-IN: merging coverage and necessity findings")
    await authorisation_manager.run(c)
    record_write(c, "decision", c.get("decision"), "Authorisation Manager")
    record_write(c, "ai_decision", c.get("ai_decision"), "Authorisation Manager")
    record_write(c, "confidence", c.get("confidence", 0), "Authorisation Manager")
    record_write(c, "cited_clauses", c.get("cited_clauses", []), "Authorisation Manager")

    if c["decision"] == "APPROVE":
        c["status"] = "COMPLETED"
        record_write(c, "status", "COMPLETED", "Authorisation Manager")
        await letter_drafter.run(c)
        record_write(c, "letter", c.get("letter", ""), "Letter Drafter")
    else:  # human routing: every denial (and more-info) goes to a human reviewer
        c["status"] = "PENDING_HUMAN_REVIEW"
        c["human_review"]["required"] = True
        record_write(c, "status", "PENDING_HUMAN_REVIEW", "Authorisation Manager")
        log(c, "Orchestrator", f"Routed to human peer reviewer ({c['decision']})")

    if persist: save()
    else: STORE.pop(c["case_id"], None)
    return c

async def apply_review(case_id, verdict, reviewer="Clinical Peer Reviewer", notes=""):
    c = STORE[case_id]
    c["human_review"].update(verdict=verdict, reviewer=reviewer, notes=notes)
    record_write(c, "human_review", c["human_review"], "Clinical Peer Reviewer")
    c["decision"] = {"UPHOLD": c["ai_decision"], "OVERTURN": "APPROVE" if c["ai_decision"] != "APPROVE" else "DENY", "REQUEST_INFO": "MORE_INFO"}[verdict]
    record_write(c, "decision", c["decision"], "Clinical Peer Reviewer")
    c["status"] = "COMPLETED"
    record_write(c, "status", "COMPLETED", "Clinical Peer Reviewer")
    log(c, "Human Reviewer", f"{verdict} by {reviewer}: final decision {c['decision']}. {notes}")
    await letter_drafter.run(c)
    record_write(c, "letter", c.get("letter", ""), "Letter Drafter")
    save()
    return c
