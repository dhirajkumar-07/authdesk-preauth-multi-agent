import json, os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .orchestrator import run_case, apply_review
from .case_record import STORE
from .evaluation import evaluate
from .rag import DATA
from . import llm

app = FastAPI(title="AuthDesk: Treatment Pre-Authorisation Decision Desk")
STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")

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
async def samples(): return json.load(open(os.path.join(DATA, "test_cases.json")))
@app.get("/mode")
async def mode(): return llm.mode()
@app.get("/")
async def index(): return FileResponse(os.path.join(STATIC, "index.html"))
app.mount("/static", StaticFiles(directory=STATIC), name="static")
