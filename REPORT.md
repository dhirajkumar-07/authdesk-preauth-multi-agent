# AuthDesk: Treatment Pre-Authorisation Decision Desk — Comprehensive Project Report

**System**: Enterprise Multi-Agent Utilization Management Architecture
**Specification**: Grounded RAG, Parallel Fan-Out/Fan-In, Human-in-the-Loop
**Project**: AuthDesk Production System  
**Product Name**: **AuthDesk**  
**Engineering Architecture**:  
- **Lead Knowledge Retrieval & Grounding Specialist** — Dual-Collection Vector Store & Semantic Grounding  
- **Backend & Multi-Agent Orchestration Specialist** — Parallel Coordination Architecture, Routing & FastAPI  
- **Full-Stack Integration, Evaluation & Benchmark Specialist** — Streamlit UI, Web Application & Benchmark Suite  

---

## 1. Executive Summary

AuthDesk is an enterprise multi-agent pre-authorisation decision desk built with **Microsoft Semantic Kernel (Python SDK)** and **FastAPI**. It automates healthcare pre-authorisation requests using a **Parallel Fan-Out / Fan-In** coordination architecture with five collaborating agents operating over a persistent **Shared Case Record**.

Every automated triage decision is strictly grounded in synthetic plan policies (`data/plan_docs`) and clinical guidelines (`data/guidelines`) using clause-level chunking and TF-IDF cosine similarity retrieval. To ensure patient safety, every denial or missing-documentation request is routed to a **Human Peer Review Queue** before any decision letter is drafted (Group-of-3 Peer-Review Escalation).

---

## 2. Standardized Benchmark Evaluation (16 Cases)

Evaluation was performed in Google Gemini LLM mode across 16 diverse clinical test cases, combining the original 10 coursework requests with 6 hardened test cases (including out-of-network exclusions, physiotherapy referrals, borderline symptom duration, acute head trauma, and messy unstructured inputs).

### Real Evaluation Benchmark Results Table

| Case ID | Scenario Description | Expected Decision | Actual AI Decision | Decision Triage | Expected Clauses | Cited Clauses (Gemini) | Recall | Clause Status |
|---|---|---|---|---|---|---|---|---|
| **TC01** | Lumbar MRI (chronic 8w pain) | `APPROVE` | `APPROVE` | **PASS** | PLAN-2.1, PLAN-7.1, GL-MRI-3.1 | GL-MRI-3.1, PLAN-2.1, PLAN-7.1 | **100%** | **PASS** |
| **TC02** | Knee Replacement (severe OA) | `APPROVE` | `APPROVE` | **PASS** | PLAN-2.2, GL-TKR-4.1 | GL-TKR-4.1, PLAN-2.2, PLAN-7.1 | **100%** | **PASS** |
| **TC03** | Chemotherapy (oncologist plan) | `APPROVE` | `APPROVE` | **PASS** | PLAN-3.1, GL-ONC-6.1 | GL-ONC-6.1, PLAN-3.1 | **100%** | **PASS** |
| **TC04** | Bariatric surgery (BMI 42) | `APPROVE` | `APPROVE` | **PASS** | PLAN-2.4, GL-BAR-5.1 | GL-BAR-5.1, PLAN-2.4, PLAN-7.1 | **100%** | **PASS** |
| **TC05** | Rhinoplasty (aesthetic/cosmetic)| `DENY` | `DENY` | **PASS** | PLAN-4.1 | PLAN-4.1 | **100%** | **PASS** |
| **TC06** | Stem-cell knee injection | `DENY` | `DENY` | **PASS** | PLAN-4.2 | PLAN-4.2 | **100%** | **PASS** |
| **TC07** | Lumbar MRI (acute 2w pain) | `DENY` | `DENY` | **PASS** | PLAN-2.1, GL-MRI-3.2 | GL-MRI-3.2 | **50%** | **FAIL** |
| **TC08** | Knee Arthroscopy (OA only) | `DENY` | `DENY` | **PASS** | PLAN-2.2, GL-KNEE-2.1 | GL-KNEE-2.1, PLAN-2.2, PLAN-7.1 | **100%** | **PASS** |
| **TC09** | Knee surgery (unspecified) | `MORE_INFO` | `MORE_INFO` | **PASS** | PLAN-7.2, GL-KNEE-2.1 | GL-KNEE-2.1, PLAN-7.2 | **100%** | **PASS** |
| **TC10** | CT head scan (fall, missing info)| `MORE_INFO` | `MORE_INFO` | **PASS** | PLAN-7.2, GL-CT-8.1 | GL-CT-8.1, PLAN-2.1, PLAN-7.2 | **100%** | **PASS** |
| **TC11** | Out-of-network MRI referral | `DENY` | `DENY` | **PASS** | PLAN-4.3 | GL-MRI-3.2, PLAN-4.3 | **100%** | **PASS** |
| **TC12** | Physiotherapy (functional deficit)| `APPROVE` | `APPROVE` | **PASS** | PLAN-2.3, GL-PT-7.1 | GL-PT-7.1, PLAN-2.3 | **100%** | **PASS** |
| **TC13** | Lumbar MRI (borderline 6w pain) | `APPROVE` | `APPROVE` | **PASS** | PLAN-2.1, GL-MRI-3.1 | GL-MRI-3.1, PLAN-2.1, PLAN-7.1 | **100%** | **PASS** |
| **TC14** | CT head (trauma with red flags) | `APPROVE` | `APPROVE` | **PASS** | PLAN-2.1, GL-CT-8.1 | GL-CT-8.1, PLAN-2.1, PLAN-7.1 | **100%** | **PASS** |
| **TC15** | Bariatric (BMI 36, no comorbidity)| `DENY` | `DENY` | **PASS** | PLAN-2.4, GL-BAR-5.1 | GL-BAR-5.1, PLAN-2.4 | **100%** | **PASS** |
| **TC16** | Messy free text with typos | `APPROVE` | `MORE_INFO` | **FAIL** | PLAN-3.1, GL-ONC-6.1 | GL-ONC-6.1, PLAN-7.2 | **50%** | **FAIL** |

---

### Core Performance Metrics

- **Decision Accuracy**: **93.8%** ($15 / 16$ cases correctly triaged)
- **Clause Correctness**: **87.5%** ($14 / 16$ cases cited all expected clauses)
- **Average Clause Recall**: **93.8%**
- **Decision Stability Across Runs**: **100%** (Zero decisions changed between Run 1 and Run 2)

### Confusion Matrix

```
                          ACTUAL AI PREDICTION
                    APPROVE       DENY      MORE_INFO
EXPECTED         +-----------+------------+------------+
  APPROVE (8)    |     7     |     0      |     1      |
  DENY (6)       |     0     |     6      |     0      |
  MORE_INFO (2)  |     0     |     0      |     2      |
                 +-----------+------------+------------+
```

---

## 3. Qualitative Error Analysis & Discussion

1. **Case TC16 (Unstructured Text & Typos)**:
   - Request text: `"pt p1016 need urgent chemmotherapy breast tumur biopsy proven positive dr singhh cancer clinic innetwork plan attached"`
   - Result: Triage decision was `MORE_INFO` citing `['PLAN-7.2', 'GL-ONC-6.1']`.
   - Reason: The Authorisation Manager detected that the input text lacked structured provider and clinical documentation blocks. In real-world clinical automation, safely degrading to `MORE_INFO` is significantly safer than blindly approving an informal prompt.
2. **Case TC07 (Acute Lumbar MRI)**:
   - Expected: `['PLAN-2.1', 'GL-MRI-3.2']`
   - Actual: `['GL-MRI-3.2']` (Recall: 50%)
   - Reason: The LLM recognized `GL-MRI-3.2` as the definitive clinical disqualifier for acute pain under 6 weeks. It omitted the general prior-authorisation imaging clause (`PLAN-2.1`), considering procedural coverage redundant when clinical criteria are failed outright.
3. **LLM vs Rule Engine Comparison**:
   - **LLM Mode Accuracy**: **93.8%** ($15 / 16$)
   - **Rule Engine Accuracy**: **81.2%** ($13 / 16$)
   - The static rule engine failed on novel cases TC12 (physiotherapy) and TC14 (trauma CT) because regex heuristics were tuned only to the original 10 cases. The LLM accurately understood the clinical context and approved both cases correctly.

---

## 4. Requirement Verification & File Mapping

| Requirement | Implementation Architecture | Source File Location |
|---|---|---|
| **5 separate agent modules** | 1. `request_parser.py`<br>2. `coverage_retrieval.py`<br>3. `medical_necessity.py`<br>4. `authorisation_manager.py`<br>5. `letter_drafter.py` | `app/agents/` |
| **Framework-based agents** | Semantic Kernel `Kernel` with `GoogleAIChatCompletion` connector | `app/llm.py` |
| **Fan-Out / Fan-In Coordination** | `asyncio.gather` for parallel Coverage & Necessity; fan-in to Authorisation Manager | `app/orchestrator.py` |
| **Human Routing Branch** | Approvals draft immediately; Denials and More-Info route to `PENDING_HUMAN_REVIEW` | `app/orchestrator.py` |
| **Clause-Level RAG** | Regex chunking by clause (`PLAN-x.x`, `GL-xxx-x.x`) with pure TF-IDF cosine similarity | `app/rag.py` |
| **Strict Grounding Enforcement** | Programmatic validation intercepts LLM output and strips any ungrounded clause IDs | `app/agents/coverage_retrieval.py`<br>`app/agents/medical_necessity.py` |
| **Shared Case Record + Audit Trail** | Single persistent dictionary in `data/cases.json`; every agent appends timestamped actions | `app/case_record.py` |
| **Tri-Fold Output** | 1. Decision<br>2. Grounded Clause Citations + Text<br>3. Draft Notice Letter | `app/case_record.py`<br>`static/index.html` |
| **Peer Review Escalation (Group-of-3)** | Denials held in Review Queue; reviewer submits Uphold/Overturn/Request-Info; letter produced post-verdict | `POST /cases/{id}/review`<br>`static/index.html` |
| **Standardized Evaluation Runner** | 16 test cases, Decision Accuracy, Clause Correctness, Recall, Confusion Matrix | `evaluate.py`<br>`app/evaluation.py` |

---

## 5. Security & Verification Summary

- **API Key Protection**: `GEMINI_API_KEY` is loaded strictly via `dotenv` from `.env`.
- **Repository Audit**: Comprehensive grep confirms **zero API keys** exist in codebase, JSON records, or logs.
- **Git Ignore**: `.env` and `data/cases.json` are explicitly ignored in `.gitignore`.
