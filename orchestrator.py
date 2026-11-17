"""Orchestrator Module:
Coordinates collaborative multi-agent execution:
  1. Parser Agent -> Structures input
  2. FAN-OUT: Coverage Retrieval & Medical Necessity execute IN PARALLEL (asyncio.gather)
  3. FAN-IN: Authorisation Manager synthesizes findings -> APPROVE / DENY / MORE_INFO
  4. Human Routing: DENY & MORE_INFO pause for Peer-Review Escalation
  5. Letter Drafter Agent -> Produces final grounded determination letter

Supports both step-by-step interactive execution and automated pipeline execution.
"""
import asyncio
from typing import Dict, Any, Tuple
from case_record import CaseRecord, create_case
from agents import (
    request_parser,
    coverage_retrieval,
    medical_necessity,
    authorisation_manager,
    letter_drafter
)

STEPS = [
    {"index": 0, "name": "Request Parser", "desc": "Extracts clinical entities, diagnoses, and provider details."},
    {"index": 1, "name": "Parallel RAG (Fan-Out)", "desc": "Executes Coverage Retrieval & Medical Necessity concurrently."},
    {"index": 2, "name": "Authorisation Manager (Fan-In)", "desc": "Synthesizes policy & clinical findings to triage APPROVE/DENY/MORE_INFO."},
    {"index": 3, "name": "Peer Review Escalation", "desc": "Human physician reviews non-approvals (Uphold/Overturn)."},
    {"index": 4, "name": "Letter Drafter", "desc": "Drafts formal clause-grounded determination letter."},
    {"index": 5, "name": "Final Determination", "desc": "Complete case record with full audit history."}
]

async def execute_step(step_idx: int, case: CaseRecord, **kwargs) -> Tuple[str, Any]:
    """Execute a single pipeline step and return (step_title, output_data)."""
    if step_idx == 0:
        parsed = await request_parser.run(case)
        return "Request Parser Output", parsed

    elif step_idx == 1:
        # Fan-Out: Run Coverage Retrieval and Medical Necessity in parallel
        case.record_write("status", "RUNNING_PARALLEL_RAG", written_by="Orchestrator")
        cov_res, nec_res = await asyncio.gather(
            coverage_retrieval.run(case),
            medical_necessity.run(case)
        )
        return "Parallel RAG Findings (Coverage & Necessity)", {
            "coverage_findings": cov_res,
            "necessity_findings": nec_res
        }

    elif step_idx == 2:
        # Fan-In: Authorisation Manager
        dec_res = await authorisation_manager.run(case)
        return "Authorisation Manager Decision", dec_res

    elif step_idx == 3:
        # Peer review step
        if case.get("decision") != "APPROVE" and not case.get("human_review", {}).get("verdict"):
            if "verdict" in kwargs:
                verdict = kwargs["verdict"]
                reviewer = kwargs.get("reviewer", "Dr. Senior Reviewer")
                notes = kwargs.get("notes", "Peer review exclusion/criteria verified.")
                return await apply_peer_review(case, verdict, reviewer, notes)
            return "Pending Peer Review Escalation", {"status": "Awaiting clinician verdict", "required": True}
        else:
            return "Human Review Skipped", {"reason": "Approval proceeded straight through or already reviewed."}

    elif step_idx == 4:
        # Letter drafter
        letter = await letter_drafter.run(case)
        case.record_write("status", "COMPLETED", written_by="Orchestrator")
        return "Final Determination Letter", letter

    return "Completed", case.to_dict()

async def apply_peer_review(case: CaseRecord, verdict: str, reviewer: str = "Dr. Senior Reviewer", notes: str = "") -> Tuple[str, Any]:
    """Peer review escalation action: writes verdict to shared case record."""
    ai_dec = case.get("ai_decision", "DENY")
    
    # Calculate final decision based on verdict
    if verdict == "UPHOLD":
        final_dec = ai_dec
    elif verdict == "OVERTURN":
        final_dec = "APPROVE" if ai_dec != "APPROVE" else "DENY"
    else:  # REQUEST_INFO
        final_dec = "MORE_INFO"

    hr_data = {
        "required": True,
        "reviewer": reviewer,
        "verdict": verdict,
        "notes": notes,
        "ai_decision_preserved": ai_dec,
        "final_decision": final_dec
    }
    
    case.record_write("human_review", hr_data, written_by="Peer Reviewer")
    case.record_write("decision", final_dec, written_by="Peer Reviewer")
    case.record_write("status", "REVIEWED", written_by="Peer Reviewer")
    
    return f"Peer Review Recorded: {verdict}", hr_data

async def run_full_pipeline(raw_request: str, auto_uphold: bool = True) -> CaseRecord:
    """Execute complete end-to-end pipeline asynchronously."""
    case = create_case(raw_request)
    
    # Step 1: Parser
    await request_parser.run(case)
    
    # Step 2: Fan-Out RAG in parallel
    await asyncio.gather(
        coverage_retrieval.run(case),
        medical_necessity.run(case)
    )
    
    # Step 3: Fan-In Authorisation Manager
    await authorisation_manager.run(case)
    
    # Step 4: Human Peer Review if DENY or MORE_INFO
    if case.get("decision") != "APPROVE":
        if auto_uphold:
            await apply_peer_review(
                case,
                verdict="UPHOLD",
                reviewer="Dr. Auto Reviewer",
                notes="Automated pipeline: AI decision upheld."
            )
            # Step 5: Draft letter on final decision
            await letter_drafter.run(case)
            case.record_write("status", "COMPLETED", written_by="Orchestrator")
    else:
        # Step 5: Draft letter immediately on approval
        await letter_drafter.run(case)
        case.record_write("status", "COMPLETED", written_by="Orchestrator")
        
    return case

