import json, os

try:
    from .orchestrator import run_case
    from .rag import DATA
except (ImportError, ValueError):
    from orchestrator import run_case
    from rag import DATA

async def evaluate():
    test_file = os.path.join(DATA, "test_requests.json")
    if not os.path.exists(test_file):
        test_file = os.path.join(DATA, "test_cases.json")
    cases = json.load(open(test_file, encoding="utf-8"))
    rows = []
    for t in cases:
        c = await run_case(t["request"], persist=False)
        exp = set(t["expected_clauses"])
        got = set(c["cited_clauses"])
        rec = len(exp & got) / len(exp) if exp else 1.0
        prec = len(exp & got) / len(got) if got else 1.0
        dec_ok = (c["ai_decision"] == t["expected_decision"])
        clause_ok = (exp <= got)  # All expected clauses were recalled
        rows.append({
            "id": t["id"],
            "expected": t["expected_decision"],
            "actual": c["ai_decision"],
            "decision_ok": dec_ok,
            "expected_clauses": sorted(exp),
            "cited_clauses": sorted(got),
            "clause_recall": round(rec, 2),
            "clause_precision": round(prec, 2),
            "clause_ok": clause_ok
        })
    n = len(rows) if rows else 1
    labels = ["APPROVE", "DENY", "MORE_INFO"]
    return {
        "total": len(rows),
        "decision_accuracy": round(sum(r["decision_ok"] for r in rows) / n, 4),
        "clause_correctness": round(sum(r["clause_ok"] for r in rows) / n, 4),
        "average_recall": round(sum(r["clause_recall"] for r in rows) / n, 4),
        "average_precision": round(sum(r["clause_precision"] for r in rows) / n, 4),
        "confusion": {e: {a: sum(r["expected"] == e and r["actual"] == a for r in rows) for a in labels} for e in labels},
        "rows": rows
    }
