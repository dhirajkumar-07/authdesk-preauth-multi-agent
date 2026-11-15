import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

def test_fastapi_endpoints():
    print("=" * 60)
    print("PHASE 4: FASTAPI ENDPOINTS AND WEB UI VERIFICATION")
    print("=" * 60)

    client = TestClient(app)

    # 1. GET /mode
    r = client.get("/mode")
    assert r.status_code == 200, f"/mode returned {r.status_code}"
    mode_data = r.json()
    assert "mode" in mode_data and "provider" in mode_data
    print(f"[PASS] GET /mode: {mode_data}")

    # 2. GET /samples
    r = client.get("/samples")
    assert r.status_code == 200
    samples = r.json()
    assert len(samples) >= 10, f"Expected at least 10 samples, got {len(samples)}"
    print(f"[PASS] GET /samples: Retrieved {len(samples)} test cases.")

    # 3. GET / (Frontend)
    r = client.get("/")
    assert r.status_code == 200
    assert "<title>AuthDesk" in r.text
    print(f"[PASS] GET /: Web UI HTML delivered successfully ({len(r.text)} bytes).")

    # 4. POST /cases (New request)
    req_body = {
        "request": "Request bariatric surgery for P-1004. Diagnosis: obesity, BMI 42, 12 months of documented supervised diet programme. Provider: Dr. Kapoor, Metro Surgical (in-network)."
    }
    r = client.post("/cases", json=req_body)
    assert r.status_code == 200, f"/cases failed: {r.text}"
    case = r.json()
    cid = case["case_id"]
    assert cid, "No case_id returned"
    assert case["decision"] == "APPROVE"
    print(f"[PASS] POST /cases: Created case {cid}, Decision={case['decision']}, Status={case['status']}")

    # 5. GET /cases
    r = client.get("/cases")
    assert r.status_code == 200
    cases_list = r.json()
    assert any(c["case_id"] == cid for c in cases_list)
    print(f"[PASS] GET /cases: Listed {len(cases_list)} cases from STORE.")

    # 6. GET /cases/{id}
    r = client.get(f"/cases/{cid}")
    assert r.status_code == 200
    assert r.json()["case_id"] == cid
    print(f"[PASS] GET /cases/{{cid}}: Retrieved case record for {cid}.")

    # 7. POST /cases (Denial case to test review endpoint)
    r_deny = client.post("/cases", json={"request": "Request rhinoplasty for P-1005 for aesthetic look. Provider: Dr. Glow."})
    deny_case = r_deny.json()
    deny_id = deny_case["case_id"]
    assert deny_case["status"] == "PENDING_HUMAN_REVIEW"

    # POST /cases/{id}/review
    rev_payload = {
        "verdict": "UPHOLD",
        "reviewer": "Dr. Peer Specialist",
        "notes": "Reviewed and confirmed aesthetic exclusion."
    }
    r = client.post(f"/cases/{deny_id}/review", json=rev_payload)
    assert r.status_code == 200
    rev_res = r.json()
    assert rev_res["status"] == "COMPLETED"
    assert rev_res["decision"] == "DENY"
    assert rev_res["human_review"]["verdict"] == "UPHOLD"
    print(f"[PASS] POST /cases/{{cid}}/review: Successfully submitted human review on case {deny_id}.")

    # 8. POST /evaluate
    print("[*] Running /evaluate via API...")
    r = client.post("/evaluate")
    assert r.status_code == 200
    ev = r.json()
    assert "decision_accuracy" in ev and "clause_correctness" in ev
    print(f"[PASS] POST /evaluate: Accuracy={int(ev['decision_accuracy']*100)}%, Clause Correctness={int(ev['clause_correctness']*100)}%")

    print("\n>>> Phase 4 (FastAPI Endpoints) completed successfully! All assertions passed.\n")

if __name__ == "__main__":
    test_fastapi_endpoints()

