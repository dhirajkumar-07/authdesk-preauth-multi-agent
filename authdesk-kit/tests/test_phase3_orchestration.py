import os, sys, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.orchestrator import run_case, apply_review

async def test_orchestration():
    print("=" * 60)
    print("PHASE 3: ORCHESTRATION AND ROUTING VERIFICATION")
    print("=" * 60)

    # 1. Test Approval Path (Instant Letter, Status COMPLETED)
    appr_req = "Request chemotherapy for P-1003. Diagnosis: biopsy-confirmed breast cancer. Written oncologist treatment plan attached. Provider: Dr. Singh, Cancer Care Centre (in-network)."
    c1 = await run_case(appr_req, persist=False)
    assert c1["ai_decision"] == "APPROVE", f"Expected APPROVE, got {c1['ai_decision']}"
    assert c1["decision"] == "APPROVE"
    assert c1["status"] == "COMPLETED", f"Expected COMPLETED status, got {c1['status']}"
    assert len(c1["letter"]) > 0, "Approval letter should be drafted immediately"
    assert not c1["human_review"]["required"], "Approval should not require human review"
    
    # Check Fan-Out / Fan-In in audit log
    actions = [l["action"] for l in c1["audit_log"]]
    assert any("FAN-OUT" in a for a in actions), "Missing FAN-OUT in audit log"
    assert any("FAN-IN" in a for a in actions), "Missing FAN-IN in audit log"
    print("[PASS] Branch 1 (APPROVE -> Instant Letter -> COMPLETED) verified.")

    # 2. Test Denial Path (Routed to Human Review, Status PENDING_HUMAN_REVIEW)
    deny_req = "Request rhinoplasty for P-1005 to improve nose shape. No breathing problems or injury reported. Provider: Dr. Sen, Glow Clinic (in-network)."
    c2 = await run_case(deny_req, persist=True)
    assert c2["ai_decision"] == "DENY", f"Expected DENY, got {c2['ai_decision']}"
    assert c2["status"] == "PENDING_HUMAN_REVIEW", f"Expected PENDING_HUMAN_REVIEW, got {c2['status']}"
    assert c2["human_review"]["required"] is True
    assert c2["letter"] == "", "Letter should NOT be drafted before human review"
    print("[PASS] Branch 2 (DENY -> PENDING_HUMAN_REVIEW -> Letter Deferred) verified.")

    # 3. Test Human Review Submission (apply_review -> Final Letter -> COMPLETED)
    c2_reviewed = await apply_review(c2["case_id"], verdict="UPHOLD", reviewer="Dr. Senior Reviewer", notes="Exclusion confirmed.")
    assert c2_reviewed["decision"] == "DENY"
    assert c2_reviewed["ai_decision"] == "DENY"
    assert c2_reviewed["status"] == "COMPLETED"
    assert len(c2_reviewed["letter"]) > 0, "Letter must be drafted after review"
    assert any("UPHOLD by Dr. Senior Reviewer" in l["action"] for l in c2_reviewed["audit_log"])
    print("[PASS] Peer Review Escalation (apply_review -> Preserved ai_decision -> Final Letter) verified.")

    # 4. Test Overturn by Human Reviewer
    deny_req2 = "Request knee arthroscopy for P-1008. Diagnosis: degenerative knee osteoarthritis only, no meniscal tear. Provider: Dr. Mehta."
    c3 = await run_case(deny_req2, persist=True)
    c3_overturned = await apply_review(c3["case_id"], verdict="OVERTURN", reviewer="Dr. Chief", notes="Clinical exception approved.")
    assert c3_overturned["ai_decision"] == "DENY", "ai_decision should remain DENY"
    assert c3_overturned["decision"] == "APPROVE", "decision should be updated to APPROVE"
    assert c3_overturned["status"] == "COMPLETED"
    print("[PASS] Peer Review Overturn (ai_decision=DENY, final decision=APPROVE) verified.")

    print("\n>>> Phase 3 (Orchestration and Routing) completed successfully! All assertions passed.\n")

if __name__ == "__main__":
    asyncio.run(test_orchestration())

