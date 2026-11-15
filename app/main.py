import json, os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .orchestrator import run_case, apply_review
from .case_record import STORE
from .evaluation import evaluate
from .rag import DATA
from . import llm

app = FastAPI(title="AuthDesk: Treatment Pre-Authorisation Decision Desk")

# Robust static directory discovery across local and serverless (Vercel) paths
_candidates = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "authdesk-kit", "static"),
    os.path.join(os.getcwd(), "static"),
    os.path.join(os.getcwd(), "authdesk-kit", "static"),
]
STATIC = next((p for p in _candidates if os.path.exists(p) and os.path.exists(os.path.join(p, "index.html"))), _candidates[0])

class NewCase(BaseModel): request: str
class Review(BaseModel): verdict: str; reviewer: str = "Peer Reviewer"; notes: str = ""

@app.post("/cases")
async def create(b: NewCase): return await run_case(b.request)

@app.get("/cases")
async def list_cases(): return sorted(STORE.values(), key=lambda c: c["created"], reverse=True)

@app.get("/cases/{cid}")
async def get_case(cid: str):
    if cid not in STORE: raise HTTPException(404, "Case not found")
    return STORE[cid]

@app.post("/cases/{cid}/review")
async def review(cid: str, b: Review):
    if cid not in STORE: raise HTTPException(404, "Case not found")
    if b.verdict not in ("UPHOLD", "OVERTURN", "REQUEST_INFO"): raise HTTPException(400, "Bad verdict")
    return await apply_review(cid, b.verdict, b.reviewer, b.notes)

@app.post("/evaluate")
async def run_eval(): return await evaluate()

@app.get("/samples")
async def samples():
    cases_file = os.path.join(DATA, "test_cases.json")
    if not os.path.exists(cases_file):
        for c in _candidates:
            alt = os.path.join(os.path.dirname(c), "data", "test_cases.json")
            if os.path.exists(alt):
                cases_file = alt; break
    return json.load(open(cases_file, encoding="utf-8"))

@app.get("/mode")
async def mode(): return llm.mode()

@app.get("/")
async def index():
    html_path = os.path.join(STATIC, "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    for c in _candidates:
        p = os.path.join(c, "index.html")
        if os.path.exists(p):
            return FileResponse(p)
    return HTMLResponse("<h1>AuthDesk backend is online. index.html loading...</h1>", status_code=200)

if os.path.exists(STATIC):
    app.mount("/static", StaticFiles(directory=STATIC), name="static")
