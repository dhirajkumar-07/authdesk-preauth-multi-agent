"""Shared Case Record: every agent reads and writes this dict. Includes the audit log and write history."""
import json, os, uuid, datetime
STORE = {}
PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "cases.json")

# Persistent storage: load existing cases from disk on startup
if os.path.exists(PATH):
    try:
        with open(PATH, "r", encoding="utf-8") as _f:
            _disk_cases = json.load(_f)
            if isinstance(_disk_cases, dict):
                STORE.update(_disk_cases)
            elif isinstance(_disk_cases, list):
                for _c in _disk_cases:
                    if isinstance(_c, dict) and "case_id" in _c:
                        STORE[_c["case_id"]] = _c
    except Exception:
        pass
now = lambda: datetime.datetime.now().isoformat(timespec="seconds")

def new_case(raw):
    c = {
        "case_id": uuid.uuid4().hex[:8],
        "created": now(),
        "raw_request": raw,
        "status": "RUNNING",
        "parsed": {},
        "coverage_findings": {},
        "necessity_findings": {},
        "decision": None,
        "ai_decision": None,
        "confidence": 0,
        "cited_clauses": [],
        "clause_text": {},
        "human_review": {"required": False, "reviewer": None, "verdict": None, "notes": None},
        "letter": "",
        "audit_log": [],
        "history": []
    }
    STORE[c["case_id"]] = c
    return c

def record_write(c, field, value, written_by):
    c[field] = value
    if "history" not in c:
        c["history"] = []
    c["history"].append({
        "field": field,
        "value": value,
        "written_by": written_by,
        "timestamp": now()
    })

def log(c, agent, action):
    c["audit_log"].append({"agent": agent, "timestamp": now(), "action": action})

def save():
    try:
        json.dump(STORE, open(PATH, "w"), indent=1)
    except OSError:
        try:
            tmp_path = os.path.join("/tmp", "cases.json")
            json.dump(STORE, open(tmp_path, "w"), indent=1)
        except OSError:
            pass
