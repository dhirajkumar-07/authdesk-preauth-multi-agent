import json, os, sys
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

_app_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_app_dir)
for _p in [_root_dir, _app_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from .orchestrator import run_case, apply_review
    from .case_record import STORE
    from .evaluation import evaluate
    from .rag import DATA
    from . import llm
except (ImportError, ValueError):
    from orchestrator import run_case, apply_review
    from case_record import STORE
    from evaluation import evaluate
    from rag import DATA
    import llm

app = FastAPI(title="AuthDesk: Treatment Pre-Authorisation Decision Desk")

# Robust directory discovery across local and serverless (Vercel) paths
_candidates = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "authdesk-kit", "static"),
    os.path.join(os.getcwd(), "static"),
    os.path.join(os.getcwd(), "authdesk-kit", "static"),
]
STATIC = next((p for p in _candidates if os.path.exists(p) and os.path.exists(os.path.join(p, "index.html"))), _candidates[0])

def _read_index_html():
    for p in [
        os.path.join(STATIC, "index.html"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "index.html"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "authdesk-kit", "static", "index.html"),
        os.path.join(os.getcwd(), "static", "index.html"),
        os.path.join(os.getcwd(), "authdesk-kit", "static", "index.html"),
    ]:
        if os.path.exists(p):
            try:
                return open(p, "r", encoding="utf-8").read()
            except Exception:
                pass
    return "<h1>AuthDesk: Treatment Pre-Authorisation Decision Desk</h1><p>Frontend loading...</p>"

class NewCase(BaseModel): request: str
class Review(BaseModel): verdict: str; reviewer: str = "Peer Reviewer"; notes: str = ""

# Root HTML UI (handles direct, /api, and Vercel internal rewritten destinations)
@app.get("/")
@app.get("/api")
@app.get("/api/")
@app.get("/api/index")
@app.get("/api/index.py")
async def index():
    return HTMLResponse(_read_index_html(), status_code=200)

# Cases endpoint
@app.post("/cases")
@app.post("/api/cases")
@app.post("/api/index.py/cases")
async def create(b: NewCase):
    return await run_case(b.request)

@app.get("/cases")
@app.get("/api/cases")
@app.get("/api/index.py/cases")
async def list_cases():
    return sorted(STORE.values(), key=lambda c: c["created"], reverse=True)

@app.get("/cases/{cid}")
@app.get("/api/cases/{cid}")
@app.get("/api/index.py/cases/{cid}")
async def get_case(cid: str):
    if cid not in STORE: raise HTTPException(404, "Case not found")
    return STORE[cid]

@app.post("/cases/{cid}/review")
@app.post("/api/cases/{cid}/review")
@app.post("/api/index.py/cases/{cid}/review")
async def review(cid: str, b: Review):
    if cid not in STORE: raise HTTPException(404, "Case not found")
    if b.verdict not in ("UPHOLD", "OVERTURN", "REQUEST_INFO"): raise HTTPException(400, "Bad verdict")
    return await apply_review(cid, b.verdict, b.reviewer, b.notes)

@app.post("/evaluate")
@app.post("/api/evaluate")
@app.post("/api/index.py/evaluate")
async def run_eval():
    return await evaluate()

@app.get("/samples")
@app.get("/api/samples")
@app.get("/api/index.py/samples")
async def samples():
    cases_file = os.path.join(DATA, "test_requests.json")
    if not os.path.exists(cases_file):
        cases_file = os.path.join(DATA, "test_cases.json")
    if not os.path.exists(cases_file):
        for c in _candidates:
            alt = os.path.join(os.path.dirname(c), "data", "test_requests.json")
            if os.path.exists(alt):
                cases_file = alt; break
            alt2 = os.path.join(os.path.dirname(c), "data", "test_cases.json")
            if os.path.exists(alt2):
                cases_file = alt2; break
    return json.load(open(cases_file, encoding="utf-8"))

@app.get("/mode")
@app.get("/api/mode")
@app.get("/api/index.py/mode")
async def mode():
    return llm.mode()

if os.path.exists(STATIC):
    app.mount("/static", StaticFiles(directory=STATIC), name="static")
