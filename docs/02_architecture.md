# Architecture

```
Request -> Request Parser -> (writes Case Record)
              |
      FAN-OUT (parallel)
      /                \
Coverage Retrieval   Medical Necessity
 (RAG: plan docs)    (RAG: guidelines)
      \                /
       FAN-IN
          |
   Authorisation Manager -> APPROVE / DENY / MORE_INFO
          |
   HUMAN ROUTING
   Approve (high confidence) -> Letter Drafter
   Deny      -> Human peer reviewer -> verdict written back -> Letter Drafter
   More Info -> Human -> request documents -> Letter Drafter
All agents read and write the SHARED CASE RECORD (with audit log).
```

## Case Record fields
case_id, raw_request, parsed{treatment, diagnosis, provider}, coverage_findings[], necessity_findings[], decision, confidence, cited_clauses[], human_review{required, reviewer, verdict, notes}, letter, audit_log[{agent, timestamp, action}]

## Tech stack
Semantic Kernel (Python), ChromaDB, FastAPI + SSE, Next.js + Tailwind + shadcn/ui + Framer Motion.
