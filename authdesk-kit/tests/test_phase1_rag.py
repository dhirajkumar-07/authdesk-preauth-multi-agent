import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.rag import COLLECTIONS, retrieve, clause_text

def test_rag():
    print("=" * 60)
    print("PHASE 1: DATA AND RAG VERIFICATION")
    print("=" * 60)

    # 1. Corpus validation
    for name, idx in COLLECTIONS.items():
        print(f"Collection: {name}")
        print(f"  Total Indexed Clauses: {len(idx.docs)}")
        assert len(idx.docs) > 0, f"No clauses found in {name}"
        sample = list(idx.docs.items())[:2]
        for cid, txt in sample:
            print(f"    - [{cid}]: {txt[:70]}...")

    # 2. Retrieval tests
    test_queries = [
        ("plan_docs", "MRI lumbar spine imaging scan", ["PLAN-2.1", "PLAN-7.1"]),
        ("plan_docs", "cosmetic surgery rhinoplasty elective", ["PLAN-4.1"]),
        ("guidelines", "low back pain 8 weeks failed physiotherapy", ["GL-MRI-3.1"]),
        ("guidelines", "severe knee osteoarthritis walking impairment", ["GL-TKR-4.1"]),
        ("guidelines", "acute back pain under 6 weeks without red flags", ["GL-MRI-3.2"]),
    ]

    print("\nRetrieval Relevance Tests:")
    for col, query, expected_any in test_queries:
        hits = retrieve(query, col, k=4)
        hit_ids = [h["clause_id"] for h in hits]
        scores = [f"{h['clause_id']}({h['score']})" for h in hits]
        matched = any(e in hit_ids for e in expected_any)
        status = "PASS" if matched else "FAIL"
        print(f"  [{status}] Query: '{query}' -> Top hits: {', '.join(scores)}")
        assert matched, f"Expected one of {expected_any} in {hit_ids}"

    # 3. Clause Text lookup
    sample_id = "PLAN-2.1"
    txt = clause_text(sample_id)
    assert len(txt) > 0, f"Failed to retrieve text for {sample_id}"
    print(f"\nClause text lookup for {sample_id}: '{txt[:80]}...'")

    print("\n>>> Phase 1 (Data and RAG) completed successfully! All assertions passed.\n")

if __name__ == "__main__":
    test_rag()

