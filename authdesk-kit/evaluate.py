import asyncio
from app.evaluation import evaluate

def main():
    print("=" * 68)
    print("AUTHDESK EVALUATION RUNNER (10 TEST CASES)")
    print("=" * 68)
    r = asyncio.run(evaluate())

    print(f"{'ID':5}{'Expected':11}{'Actual':11}{'Dec':6}{'Recall':8}{'Clauses OK':12}{'Cited Clauses'}")
    print("-" * 68)
    for x in r["rows"]:
        dec_st = "PASS" if x["decision_ok"] else "FAIL"
        cl_st = "PASS" if x["clause_ok"] else "FAIL"
        print(f"{x['id']:5}{x['expected']:11}{x['actual']:11}{dec_st:6}{x['clause_recall']:<8.0%}{cl_st:12}{x['cited_clauses']}")

    print("\n" + "=" * 35 + " METRICS " + "=" * 35)
    print(f"Decision Accuracy  : {r['decision_accuracy']:.1%} ({sum(x['decision_ok'] for x in r['rows'])}/{len(r['rows'])} cases)")
    print(f"Clause Correctness : {r['clause_correctness']:.1%} ({sum(x['clause_ok'] for x in r['rows'])}/{len(r['rows'])} cases)")
    avg_recall = sum(x["clause_recall"] for x in r["rows"]) / len(r["rows"])
    print(f"Average Recall     : {avg_recall:.1%}")

    print("\n" + "=" * 30 + " CONFUSION MATRIX " + "=" * 30)
    labels = ["APPROVE", "DENY", "MORE_INFO"]
    print(f"{'Expected \\ Actual':20}" + "".join(f"{l:>12}" for l in labels))
    for exp in labels:
        row_str = f"{exp:20}" + "".join(f"{r['confusion'][exp][act]:>12}" for act in labels)
        print(row_str)
    print("=" * 79)

if __name__ == "__main__":
    main()
