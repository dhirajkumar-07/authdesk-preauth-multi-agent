"""Shared Case Record: every agent reads and writes this dict. Includes the audit log."""
import json, os, uuid, datetime
STORE = {}
PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "cases.json")
now = lambda: datetime.datetime.now().isoformat(timespec="seconds")

def new_case(raw):
    c = {"case_id": uuid.uuid4().hex[:8], "created": now(), "raw_request": raw, "status": "RUNNING",
         "parsed": {}, "coverage_findings": {}, "necessity_findings": {}, "decision": None, "ai_decision": None,
         "confidence": 0, "cited_clauses": [], "clause_text": {},
         "human_review": {"required": False, "reviewer": None, "verdict": None, "notes": None},
         "letter": "", "audit_log": []}
    STORE[c["case_id"]] = c
    return c

def log(c, agent, action):
    c["audit_log"].append({"agent": agent, "timestamp": now(), "action": action})

def save():
    try: json.dump(STORE, open(PATH, "w"), indent=1)
    except OSError:
        try:
            tmp_path = os.path.join("/tmp", "cases.json")
            json.dump(STORE, open(tmp_path, "w"), indent=1)
        except OSError:
            pass
