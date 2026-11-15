# Step-by-step plan

1. Create workspace `preauth-desk` in Antigravity, choose Planning mode, put API key in `.env`.
2. Paste prompts/backend_prompt.md and approve the plan artifact.
3. Use the provided data/ folder (or have the agent extend it).
4. Build the RAG layer: chunk by clause, keep clause ID in metadata, two Chroma collections (plan_docs, guidelines), `retrieve(query, collection, k=4)`.
5. Build the shared Case Record (Pydantic + SQLite/JSON) with an audit log.
6. Build five agents, one module each, strict JSON output:
   request_parser, coverage_retrieval, medical_necessity, authorisation_manager, letter_drafter.
7. Orchestration: fan-out (Coverage + Necessity via asyncio.gather), fan-in (Authorisation Manager), router for human routing.
8. FastAPI: POST /cases, GET /cases, GET /cases/{id}, GET /cases/{id}/stream (SSE), POST /cases/{id}/review, POST /evaluate.
9. Frontend: paste prompts/ui_prompt.md.
10. Peer-review escalation: every denial sets PENDING_HUMAN_REVIEW; the verdict is written back to the Case Record, then the letter is drafted.
11. Evaluation: run the 10 cases, report decision accuracy and clause correctness, confusion matrix, per-case table.
12. Use the Antigravity browser agent to test and capture screenshots, record the demo, write the README with the contribution split.

## Deliverables checklist
- [ ] 5 separate agent modules
- [ ] Fan-out/fan-in orchestration + diagram
- [ ] RAG over plan docs and guidelines + shared Case Record
- [ ] Output: decision + clauses + draft letter
- [ ] Evaluation table (10 cases)
- [ ] Peer-review escalation with verdict written back
- [ ] Demo video and screenshots
- [ ] README with setup and contribution split

## Viva tips
- Coverage and Necessity run in parallel because they are independent, which cuts latency.
- Denials always escalate for patient safety and accountability.
