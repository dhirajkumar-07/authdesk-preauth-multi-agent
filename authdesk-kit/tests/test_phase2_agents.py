import os, sys, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.case_record import new_case, log, STORE
from app.agents import request_parser, coverage_retrieval, medical_necessity, authorisation_manager, letter_drafter

async def test_agents():
    print("=" * 60)
    print("PHASE 2: CASE RECORD AND AGENTS VERIFICATION")
    print("=" * 60)

    # 1. Test case creation and schema
    raw_sample = "Request MRI lumbar spine for patient P-1001. Diagnosis: chronic low back pain for 8 weeks, failed 6 weeks of physiotherapy. Provider: Dr. Rao, City Ortho (in-network)."
    c = new_case(raw_sample)
    assert c["case_id"] in STORE, "Case not registered in STORE"
    expected_fields = ["case_id", "created", "raw_request", "status", "parsed", "coverage_findings", 
                       "necessity_findings", "decision", "ai_decision", "confidence", "cited_clauses", 
                       "clause_text", "human_review", "letter", "audit_log"]
    for f in expected_fields:
        assert f in c, f"Missing field {f} in case record"
    print("[PASS] Case record initialization and schema verified.")

    # 2. Agent 1: Request Parser
    await request_parser.run(c)
    assert c["parsed"]["patient"] == "P-1001", f"Parsed patient incorrect: {c['parsed']}"
    assert "mri" in c["parsed"]["treatment"].lower(), f"Parsed treatment incorrect: {c['parsed']}"
    print(f"[PASS] Agent 1 (Request Parser): {c['parsed']}")

    # 3. Agent 2: Coverage Retrieval
    await coverage_retrieval.run(c)
    cov = c["coverage_findings"]
    assert cov["status"] in ("COVERED_PRIOR_AUTH", "EXCLUDED", "UNCLEAR")
    assert len(cov["clauses"]) > 0, "No coverage clauses cited"
    print(f"[PASS] Agent 2 (Coverage Retrieval): Status={cov['status']}, Clauses={cov['clauses']}")

    # 4. Agent 3: Medical Necessity
    await medical_necessity.run(c)
    nec = c["necessity_findings"]
    assert nec["status"] in ("MET", "NOT_MET", "INSUFFICIENT", "NOT_APPLICABLE")
    assert len(nec["clauses"]) > 0 or nec["status"] == "NOT_APPLICABLE"
    print(f"[PASS] Agent 3 (Medical Necessity): Status={nec['status']}, Clauses={nec['clauses']}")

    # 5. Agent 4: Authorisation Manager
    await authorisation_manager.run(c)
    assert c["decision"] in ("APPROVE", "DENY", "MORE_INFO")
    assert c["ai_decision"] == c["decision"]
    assert len(c["cited_clauses"]) > 0
    # Grounding check: all cited clauses must have text
    for cid in c["cited_clauses"]:
        assert cid in c["clause_text"], f"Missing text for cited clause {cid}"
    print(f"[PASS] Agent 4 (Authorisation Manager): Decision={c['decision']}, Cited={c['cited_clauses']}")

    # 6. Agent 5: Letter Drafter
    await letter_drafter.run(c)
    assert len(c["letter"]) > 50, "Letter not drafted or too short"
    for cid in c["cited_clauses"]:
        assert cid in c["letter"], f"Letter does not cite clause ID {cid}"
    print(f"[PASS] Agent 5 (Letter Drafter): Letter generated ({len(c['letter'])} chars), citing all clauses.")

    # 7. Audit log verification
    agents_logged = [entry["agent"] for entry in c["audit_log"]]
    for agent_name in ["Request Parser", "Coverage Retrieval", "Medical Necessity", "Authorisation Manager", "Letter Drafter"]:
        assert agent_name in agents_logged, f"Agent {agent_name} did not record in audit log"
    print(f"[PASS] Shared Memory Audit Trail: {len(c['audit_log'])} chronological entries recorded.")

    print("\n>>> Phase 2 (Case Record and Agents) completed successfully! All assertions passed.\n")

if __name__ == "__main__":
    asyncio.run(test_agents())

