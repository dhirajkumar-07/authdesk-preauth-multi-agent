"""Shared Case Record: one JSON-compatible record that every agent reads and writes.
Each write stores {field, value, written_by, timestamp} in an append-only audit trail."""
import uuid
import datetime
from typing import Any, Dict, List

def now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")

class CaseRecord:
    def __init__(self, raw_request: str, case_id: str = None):
        self.case_id = case_id or uuid.uuid4().hex[:8]
        self.created = now_iso()
        
        # Internal state dictionary (the single JSON case record)
        self.data: Dict[str, Any] = {
            "case_id": self.case_id,
            "created": self.created,
            "raw_request": raw_request,
            "parsed": {},
            "coverage_findings": {},
            "necessity_findings": {},
            "decision": None,
            "ai_decision": None,
            "confidence": 0.0,
            "cited_clauses": [],
            "clause_text": {},
            "human_review": {
                "required": False,
                "reviewer": None,
                "verdict": None,
                "notes": None,
                "timestamp": None
            },
            "letter": "",
            "status": "INITIALIZED"
        }
        
        # Audit log tracking every write: {field, value, written_by, timestamp}
        self.history: List[Dict[str, Any]] = []
        self.record_write("raw_request", raw_request, written_by="Requester")

    def record_write(self, field: str, value: Any, written_by: str) -> Dict[str, Any]:
        """Record a field update with provenance metadata."""
        entry = {
            "field": field,
            "value": value,
            "written_by": written_by,
            "timestamp": now_iso()
        }
        self.history.append(entry)
        self.data[field] = value
        return entry

    def __getitem__(self, item: str):
        return self.data[item]

    def __setitem__(self, key: str, value: Any):
        self.data[key] = value

    def __contains__(self, item: str):
        return item in self.data

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        d = dict(self.data)
        d["history"] = list(self.history)
        return d

# Global in-memory store for case management
STORE: Dict[str, CaseRecord] = {}

def create_case(raw_request: str, case_id: str = None) -> CaseRecord:
    rec = CaseRecord(raw_request, case_id)
    STORE[rec.case_id] = rec
    return rec

def get_case(case_id: str) -> CaseRecord:
    return STORE.get(case_id)

