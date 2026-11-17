"""Evaluation Benchmark Runner:
Evaluates the multi-agent system on data/test_requests.json across:
  1. Decision Accuracy (Triage correctness)
  2. Clause Correctness (Strict match)
  3. Clause Precision and Recall
  4. Confusion Matrix Analysis
"""
import os
import json
import asyncio
from typing import List, Dict, Any
from orchestrator import run_full_pipeline

TEST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "test_requests.json")

def calculate_metrics(expected_clauses: List[str], actual_clauses: List[str]):
    exp_set = set(expected_clauses)
    act_set = set(actual_clauses)
    tp = len(exp_set & act_set)
    precision = tp / len(act_set) if act_set else 1.0
    recall = tp / len(exp_set) if exp_set else 1.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1

async def run_evaluation():
    if not os.path.exists(TEST_FILE):
        print(f"Error: {TEST_FILE} not found.")
        return

    with open(TEST_FILE, encoding="utf-8") as f:
        cases = json.load(f)

    print("================================================================================")
    print("AUTHDESK: TREATMENT PRE-AUTHORISATION MULTI-AGENT EVALUATION BENCHMARK")
    print(f"Total Test Requests: {len(cases)}")
    print("================================================================================\n")

    results = []
    confusion = {
        "APPROVE": {"APPROVE": 0, "DENY": 0, "MORE_INFO": 0},
        "DENY": {"APPROVE": 0, "DENY": 0, "MORE_INFO": 0},
        "MORE_INFO": {"APPROVE": 0, "DENY": 0, "MORE_INFO": 0}
    }

    correct_decisions = 0
    correct_clauses = 0
    total_prec = 0.0
    total_rec = 0.0

    for item in cases:
        req_id = item["id"]
        raw = item["request"]
        exp_dec = item["expected_decision"]
        exp_cls = item["expected_clauses"]

        # Run pipeline with auto_uphold so AI decisions reflect raw triage
        case = await run_full_pipeline(raw, auto_uphold=True)
        act_dec = case.get("ai_decision") or case.get("decision")
        act_cls = case.get("cited_clauses", [])

        dec_match = (act_dec == exp_dec)
        if dec_match:
            correct_decisions += 1

        prec, rec, f1 = calculate_metrics(exp_cls, act_cls)
        total_prec += prec
        total_rec += rec
        
        # Strict clause match (all expected clauses present)
        cls_match = set(exp_cls).issubset(set(act_cls))
        if cls_match:
            correct_clauses += 1

        if exp_dec in confusion and act_dec in confusion[exp_dec]:
            confusion[exp_dec][act_dec] += 1

        results.append({
            "id": req_id,
            "expected_decision": exp_dec,
            "actual_decision": act_dec,
            "dec_pass": dec_match,
            "expected_clauses": exp_cls,
            "actual_clauses": act_cls,
            "precision": prec,
            "recall": rec,
            "cls_pass": cls_match
        })

    n = len(cases)
    dec_acc = (correct_decisions / n) * 100
    cls_acc = (correct_clauses / n) * 100
    avg_prec = (total_prec / n) * 100
    avg_rec = (total_rec / n) * 100

    # Print Results Table
    print(f"{'ID':<8} | {'EXPECTED':<10} | {'ACTUAL':<10} | {'DEC':<5} | {'EXPECTED CLAUSES':<28} | {'ACTUAL CLAUSES':<32} | {'RECALL':<6}")
    print("-" * 115)
    for r in results:
        dec_status = "PASS" if r["dec_pass"] else "FAIL"
        exp_c_str = ", ".join(r["expected_clauses"])
        act_c_str = ", ".join(r["actual_clauses"])
        rec_str = f"{int(r['recall']*100)}%"
        print(f"{r['id']:<8} | {r['expected_decision']:<10} | {r['actual_decision']:<10} | {dec_status:<5} | {exp_c_str:<28} | {act_c_str:<32} | {rec_str:<6}")

    print("\n" + "=" * 50)
    print("EXECUTIVE SUMMARY METRICS")
    print("=" * 50)
    print(f"Decision Accuracy      : {dec_acc:.1f}% ({correct_decisions}/{n})")
    print(f"Clause Correctness     : {cls_acc:.1f}% ({correct_clauses}/{n})")
    print(f"Average Clause Recall  : {avg_rec:.1f}%")
    print(f"Average Clause Prec.   : {avg_prec:.1f}%")

    print("\nCONFUSION MATRIX:")
    print("                      ACTUAL PREDICTION")
    print("                  APPROVE   DENY   MORE_INFO")
    for exp in ["APPROVE", "DENY", "MORE_INFO"]:
        row = confusion[exp]
        print(f"EXPECTED {exp:<9} |   {row['APPROVE']:<5}   {row['DENY']:<5}    {row['MORE_INFO']:<5}")
    print("=" * 50)

    return {
        "accuracy": dec_acc,
        "clause_correctness": cls_acc,
        "recall": avg_rec,
        "results": results,
        "confusion": confusion
    }

if __name__ == "__main__":
    asyncio.run(run_evaluation())
