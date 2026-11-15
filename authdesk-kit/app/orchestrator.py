"""Fan-out / fan-in orchestration with human routing."""
import asyncio
from .case_record import STORE, new_case, log, save
from .agents import request_parser, coverage_retrieval, medical_necessity, authorisation_manager, letter_drafter

async def run_case(raw, persist=True):
    c = new_case(raw)
    await request_parser.run(c)
    log(c, "Orchestrator", "FAN-OUT: Coverage Retrieval and Medical Necessity in parallel")
    await asyncio.gather(coverage_retrieval.run(c), medical_necessity.run(c))
    log(c, "Orchestrator", "FAN-IN: findings merged")
    await authorisation_manager.run(c)
    if c["decision"] == "APPROVE":
        c["status"] = "COMPLETED"; await letter_drafter.run(c)
    else:  # human routing: every denial (and more-info) goes to a human reviewer
        c["status"] = "PENDING_HUMAN_REVIEW"; c["human_review"]["required"] = True
        log(c, "Orchestrator", f"Routed to human peer reviewer ({c['decision']})")
    if persist: save()
    else: STORE.pop(c["case_id"], None)
    return c

async def apply_review(case_id, verdict, reviewer="Peer Reviewer", notes=""):
    c = STORE[case_id]
    c["human_review"].update(verdict=verdict, reviewer=reviewer, notes=notes)
    c["decision"] = {"UPHOLD": c["ai_decision"], "OVERTURN": "APPROVE" if c["ai_decision"] != "APPROVE" else "DENY", "REQUEST_INFO": "MORE_INFO"}[verdict]
    c["status"] = "COMPLETED"
    log(c, "Human Reviewer", f"{verdict} by {reviewer}: final decision {c['decision']}. {notes}")
    await letter_drafter.run(c); save()
    return c
