import asyncio, json, os, copy
from dotenv import load_dotenv
load_dotenv()

# Ensure we are in authdesk-kit directory
from app.evaluation import evaluate
from app.orchestrator import run_case
from app.rag import DATA

async def run_detailed_eval():
    print("====================================================================")
    print("STARTING HARDENED EVALUATION ON 16 CASES (GEMINI LLM RUN 1)")
    print("====================================================================")
    cases = json.load(open(os.path.join(DATA, "test_cases.json")))
    print(f"Loaded {len(cases)} test cases.")

    # 1. RUN 1: LLM Mode
    os.environ.pop("FORCE_RULES", None)
    run1 = await evaluate()

    # Detailed audit logs for Run 1 cases to examine failure reasons
    detailed_cases_run1 = []
    for t in cases:
        c = await run_case(t["request"], persist=False)
        detailed_cases_run1.append(c)

    print("\n====================================================================")
    print("STARTING HARDENED EVALUATION ON 16 CASES (GEMINI LLM RUN 2)")
    print("====================================================================")
    # 2. RUN 2: LLM Mode (Stability Check)
    run2 = await evaluate()

    print("\n====================================================================")
    print("STARTING HARDENED EVALUATION ON 16 CASES (RULE ENGINE: FORCE_RULES=1)")
    print("====================================================================")
    # 3. RUN 3: Rule Engine Mode (FORCE_RULES=1)
    os.environ["FORCE_RULES"] = "1"
    run_rules = await evaluate()
    os.environ.pop("FORCE_RULES", None)

    # Compile results dictionary
    results = {
        "run1": run1,
        "run2": run2,
        "run_rules": run_rules,
        "detailed_run1": detailed_cases_run1,
        "cases": cases
    }

    with open("eval_hardening_data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    print("\nAll 3 evaluation passes completed and saved to eval_hardening_data.json.")

if __name__ == "__main__":
    asyncio.run(run_detailed_eval())
