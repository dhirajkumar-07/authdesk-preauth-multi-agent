# Phase prompts (send one at a time after the plan is approved)

1. Implement the RAG layer with clause-level chunking, using the files in data/. Keep clause IDs in metadata.
2. Implement the Case Record and all five agents with strict JSON schemas.
3. Implement orchestration and routing, plus a CLI script that runs one case end to end.
4. Implement the FastAPI endpoints with SSE streaming.
5. Implement the frontend using prompts/ui_prompt.md.
6. Implement the evaluation runner and the Evaluation page.
7. Use the browser agent to test the full flow (one approve, one deny with human review, the evaluation page) and capture screenshots.
