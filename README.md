# AuthDesk: Treatment Pre-Authorisation Decision Desk

**Course**: CSE476 Agentic AI and Intelligent Automation — Task 2 (Project 2), CO3 & CO4 (30 Marks)  
**Project**: Q24, Group 24  
**Group Members**:  
- **Ansh Ojha** (12312163) — Agents, Grounding & RAG  
- **Nitin Sheshma** (12326213) — Orchestration, Architecture & API  
- **Dhiraj Kumar** (12320690) — UI, Evaluation & Report  

> [!NOTE]  
> **Synthetic Data Disclaimer**: All insurance policy documents (`data/plan_docs`) and clinical guideline documents (`data/guidelines`) are synthetic academic test fixtures designed solely for this coursework project. They do not constitute actual medical guidelines or clinical advice.

---

## Architecture Diagram

```
                              [Incoming Pre-Auth Request]
                                          |
                                          v
                              [1. Request Parser Agent]
                                          |
                     +--------------------+--------------------+
                     |                                         |
                     v (Fan-Out: Parallel asyncio.gather)       v
         [2. Coverage Retrieval Agent]             [3. Medical Necessity Agent]
         (RAG: Plan Docs -> PLAN-x.x)              (RAG: Guidelines -> GL-xxx-x.x)
                     |                                         |
                     +--------------------+--------------------+
                                          |
                                          v (Fan-In: Aggregate)
                            [4. Authorisation Manager]
                            (Decision: APPROVE/DENY/MORE_INFO)
                                          |
                     +--------------------+--------------------+
                     |                                         |
          (Decision == APPROVE)                     (DENY or MORE_INFO)
                     |                                         |
                     v                                         v
          [5. Letter Drafter Agent]               [Peer-Review Queue (Escalation)]
                     |                            (Status: PENDING_HUMAN_REVIEW)
                     v                                         |
            [Status: COMPLETED]                   [Human Reviewer Action]
                                                  (UPHOLD / OVERTURN / REQUEST_INFO)
                                                               |
                                                               v
                                                  [5. Letter Drafter Agent]
                                                  (Drafts Post-Review Letter)
                                                               |
                                                               v
                                                      [Status: COMPLETED]
```

---

## Setup & Running

### 1. Installation
```powershell
pip install -r requirements.txt
```

### 2. Configure Environment Key
Copy `.env.example` to `.env` and set your key (or leave empty / `FORCE_RULES=1` for rule-engine fallback):
```env
GEMINI_API_KEY=your_gemini_api_key_here
LLM_MODEL=gemini-3.1-flash-lite
```

### 3. Verify Connector
```powershell
python check_llm.py
```
Expected output:
```json
{"mode": "LLM (Semantic Kernel)", "provider": "gemini", "model": "gemini-3.1-flash-lite"}
{"ok": true}
```

### 4. Run CLI Runner (Single Case Demonstration)
```powershell
python cli.py
```

### 5. Launch FastAPI Web Desk
```powershell
uvicorn app.main:app --reload
```
Open **http://127.0.0.1:8000** in your browser. The top-right chip shows `LLM (Semantic Kernel)` or `RULES (no API key)`.

### 6. Run Evaluation Suite (16 Benchmark Cases)
```powershell
python evaluate.py
```
Detailed results, confusion matrix, side-by-side LLM vs Rule comparison, and viva analysis are documented in [REPORT.md](REPORT.md), [EVAL_RESULTS.md](EVAL_RESULTS.md), and [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

---

## Requirement Checklist (Q24)

| Requirement | Where Implemented | Verification Test |
|---|---|---|
| **Framework-based agents (Semantic Kernel)** | `app/llm.py`, registered in Semantic Kernel `Kernel`; all 5 agents call `llm.with_fallback` | `python check_llm.py` |
| **5 agents, each a separate module** | `app/agents/request_parser.py`<br>`app/agents/coverage_retrieval.py`<br>`app/agents/medical_necessity.py`<br>`app/agents/authorisation_manager.py`<br>`app/agents/letter_drafter.py` | `python tests/test_phase2_agents.py` |
| **Fan-out / fan-in + human routing** | `app/orchestrator.py` (`asyncio.gather` for parallel Coverage & Necessity; non-approvals routed to human) | `python tests/test_phase3_orchestration.py` |
| **Clause-level RAG over plan & guideline docs** | `app/rag.py` (regex chunking by clause ID `PLAN-x.x` and `GL-xxx-x.x`, TF-IDF cosine similarity index) | `python tests/test_phase1_rag.py` |
| **Strict Grounding Enforcement** | `app/agents/*.py` (agents only see retrieved clauses; cited IDs validated against retrieved set) | `tests/test_phase2_agents.py` |
| **Shared case record + full audit log** | `app/case_record.py` (`case_id`, `raw_request`, `parsed`, findings, decisions, `audit_log`, etc.) | `tests/test_phase2_agents.py` |
| **Output: decision + clauses + draft letter** | Case record schema, `cli.py`, and Web UI (`static/index.html`) | `python cli.py` |
| **Group-of-3 Peer-Review Escalation** | `app/orchestrator.py` (`apply_review`), API `POST /cases/{id}/review`, Review Queue UI | `tests/test_phase3_orchestration.py` |
| **10 test cases & evaluation metrics** | `data/test_cases.json`, `app/evaluation.py`, `evaluate.py` (Accuracy, Correctness, Recall, Confusion Matrix) | `python evaluate.py` |

---

## How Grounding Works (Viva Explanation)

1. **Clause-Level Chunking**: Documents are chunked strictly at clause boundaries (`PLAN-x.x`, `GL-xxx-x.x`), keeping the clause ID as metadata.
2. **Context Window Isolation**: Each LLM agent prompt receives **only** the top-k clauses retrieved by RAG for that specific query. Agents are instructed never to use outside knowledge.
3. **Programmatic Validation**: When the model returns a list of cited clause IDs, the system intercepts and validates them against `{h['clause_id'] for h in retrieved_hits}`. Any hallucinatory ID not in the retrieved set is discarded.
4. **Deterministic Fail-Safe**: If the LLM generates invalid JSON, ungrounded IDs, or hits API quota limits (429), it immediately falls back to the deterministic rule engine and records `used rule fallback` in the audit log.

---

## Honest Limitations

- **Free-Tier API Rate Limits**: Free Gemini API keys have a strict daily quota (e.g. 20 requests/day on standard flash models). We configure `gemini-3.1-flash-lite` which has higher availability, and implemented a fail-fast fallback so requests never hang.
- **TF-IDF Retrieval**: The default RAG engine uses TF-IDF cosine similarity over synthetic markdown documents. In production with thousands of pages, swap `app/rag.py` with vector embeddings (ChromaDB / FAISS) using the same `retrieve(query, collection, k)` signature.
- **Human Routing Scope**: In this prototype, approval cases are finalized immediately, while denials and requests for more information are held in `PENDING_HUMAN_REVIEW` until a clinician or peer reviewer submits their verdict.
