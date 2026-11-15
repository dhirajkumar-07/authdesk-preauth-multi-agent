import json, os
from .orchestrator import run_case
from .rag import DATA
async def evaluate():
    cases = json.load(open(os.path.join(DATA, "test_cases.json"))); rows = []
    for t in cases:
        c = await run_case(t["request"], persist=False)
        exp = set(t["expected_clauses"]); got = set(c["cited_clauses"]); rec = len(exp & got) / len(exp)
        rows.append({"id": t["id"], "expected": t["expected_decision"], "actual": c["ai_decision"], "decision_ok": c["ai_decision"] == t["expected_decision"],
                     "expected_clauses": sorted(exp), "cited_clauses": sorted(got), "clause_recall": round(rec, 2), "clause_ok": exp <= got})
    n = len(rows); labels = ["APPROVE", "DENY", "MORE_INFO"]
    return {"decision_accuracy": sum(r["decision_ok"] for r in rows) / n, "clause_correctness": sum(r["clause_ok"] for r in rows) / n,
            "confusion": {e: {a: sum(r["expected"] == e and r["actual"] == a for r in rows) for a in labels} for e in labels}, "rows": rows}
