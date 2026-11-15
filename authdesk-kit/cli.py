"""CLI runner for Treatment Pre-Authorisation Decision Desk.
Runs a single case through the full orchestration pipeline with human routing.
Usage: python cli.py ["optional request text"]
"""
import sys, asyncio, json
from app.orchestrator import run_case, apply_review

DEFAULT_REQUEST = (
    "Request MRI lumbar spine for patient P-1007. "
    "Diagnosis: low back pain for 2 weeks, no weakness, numbness or other red flags, "
    "no prior treatment tried. Provider: Dr. Rao, City Ortho (in-network)."
)

async def main():
    req = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REQUEST
    print("=" * 65)
    print("AUTHDESK: MULTI-AGENT DECISION DESK (CLI)")
    print("=" * 65)
    print(f"INPUT REQUEST:\n{req}\n")

    print("[*] Running Orchestrator pipeline...")
    case = await run_case(req, persist=True)

    print("\n--- CASE SUMMARY ---")
    print(f"Case ID      : {case['case_id']}")
    print(f"Patient      : {case['parsed'].get('patient') or 'N/A'}")
    print(f"Treatment    : {case['parsed'].get('treatment')}")
    print(f"AI Decision  : {case['ai_decision']} (Confidence: {int(case['confidence']*100)}%)")
    print(f"Status       : {case['status']}")
    print(f"Cited Clauses: {', '.join(case['cited_clauses'])}")

    print("\n--- AUDIT LOG TRAIL ---")
    for log in case["audit_log"]:
        print(f"  [{log['timestamp'][11:]}] {log['agent']}: {log['action']}")

    # If routed to human review, demonstrate peer-review escalation
    if case["status"] == "PENDING_HUMAN_REVIEW":
        print("\n" + "=" * 65)
        print("PEER-REVIEW ESCALATION TRIGGERED")
        print("=" * 65)
        print(f"Case routed to human reviewer because AI decision is: {case['ai_decision']}")
        print("Simulating Peer Reviewer Action: UPHOLD denial with clinical notes...")
        
        # Apply review
        case = await apply_review(
            case["case_id"], 
            verdict="UPHOLD", 
            reviewer="Dr. Sarah Jenkins (Chief Medical Officer)", 
            notes="Agreed with AI finding: criteria for acute imaging under 6 weeks not met."
        )

        print(f"\nFinal Decision Post-Review : {case['decision']}")
        print(f"AI Decision (Preserved)    : {case['ai_decision']}")
        print(f"Final Status               : {case['status']}")

    print("\n--- FINAL DECISION LETTER ---")
    print(case["letter"])
    print("\n" + "=" * 65)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 65)

if __name__ == "__main__":
    asyncio.run(main())

