import asyncio, json, os, copy
from dotenv import load_dotenv

# Ensure we are running from authdesk-kit
os.chdir(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app.evaluation import evaluate
from app.orchestrator import run_case
from app.rag import DATA

async def run_suite():
    cases = json.load(open(os.path.join(DATA, "test_cases.json")))
    print(f"Total test cases loaded: {len(cases)}")

    # ==========================================
    # 1. RUN 1: GEMINI LLM MODE
    # ==========================================
    os.environ.pop("FORCE_RULES", None)
    print("\n--- Executing Run 1 (Gemini LLM) ---")
    run1 = await evaluate()
    
    # Also collect full audit logs for Run 1 cases
    detailed_run1 = []
    for t in cases:
        c = await run_case(t["request"], persist=False)
        detailed_run1.append({
            "id": t["id"],
            "expected_decision": t["expected_decision"],
            "expected_clauses": t["expected_clauses"],
            "ai_decision": c["ai_decision"],
            "cited_clauses": c["cited_clauses"],
            "audit_log": c["audit_log"]
        })

    # ==========================================
    # 2. RUN 2: GEMINI LLM MODE (STABILITY CHECK)
    # ==========================================
    print("\n--- Executing Run 2 (Gemini LLM Stability Check) ---")
    run2 = await evaluate()

    # Compare Run 1 vs Run 2
    stability_diffs = []
    for r1_row, r2_row in zip(run1["rows"], run2["rows"]):
        if r1_row["actual"] != r2_row["actual"]:
            stability_diffs.append({
                "id": r1_row["id"],
                "run1": r1_row["actual"],
                "run2": r2_row["actual"]
            })

    # ==========================================
    # 3. RUN 3: RULE ENGINE MODE (FORCE_RULES=1)
    # ==========================================
    print("\n--- Executing Run 3 (Rule Engine: FORCE_RULES=1) ---")
    os.environ["FORCE_RULES"] = "1"
    run_rules = await evaluate()
    os.environ.pop("FORCE_RULES", None)

    output = {
        "run1": run1,
        "run2": run2,
        "run_rules": run_rules,
        "stability_diffs": stability_diffs,
        "detailed_run1": detailed_run1
    }

    with open("eval_results_raw.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    print("\n=== SUMMARY OF RUNS ===")
    print(f"Run 1 LLM: Accuracy = {run1['decision_accuracy']:.1%}, Clause Correctness = {run1['clause_correctness']:.1%}")
    print(f"Run 2 LLM: Accuracy = {run2['decision_accuracy']:.1%}, Clause Correctness = {run2['clause_correctness']:.1%}")
    print(f"Decisions Changed between Run 1 & Run 2: {len(stability_diffs)}")
    print(f"Rule Engine (FORCE_RULES=1): Accuracy = {run_rules['decision_accuracy']:.1%}, Clause Correctness = {run_rules['clause_correctness']:.1%}")

if __name__ == "__main__":
    asyncio.run(run_suite())
