"""RAG Module using ChromaDB with dual collections:
  1. plan_documents (Insurance coverage policies)
  2. clinical_guidelines (Evidence-based clinical guidelines)

Features an offline, deterministic embedding function that requires zero external network downloads or API keys.
"""
import os
import glob
import re
import math
from typing import List, Dict, Any

try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    chromadb = None
    HAS_CHROMADB = False

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CLAUSE_REGEX = re.compile(r"^((?:PLAN|GL)(?:-[A-Z]+)?-\d+\.\d+)\s+(.+)$")

def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())

if HAS_CHROMADB:
    class LocalDeterministicEmbedding(chromadb.EmbeddingFunction):
        """Fast, deterministic, 128-dimensional embedding function running 100% offline."""
        def __init__(self, dim: int = 128):
            self.dim = dim

        def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
            embeddings = []
            for text in input:
                tokens = tokenize(text)
                vec = [0.0] * self.dim
                for t in tokens:
                    idx = abs(hash(t)) % self.dim
                    vec[idx] += 1.0
                norm = math.sqrt(sum(v * v for v in vec)) or 1.0
                embeddings.append([v / norm for v in vec])
            return embeddings
else:
    class LocalDeterministicEmbedding:
        def __init__(self, dim: int = 128):
            self.dim = dim

class RAGEngine:
    def __init__(self):
        self.clause_lookup: Dict[str, str] = {}
        self.plan_dict = {}
        self.guide_dict = {}
        if HAS_CHROMADB:
            self.client = chromadb.Client()
            self.embedding_fn = LocalDeterministicEmbedding()
            self.plan_coll = self.client.get_or_create_collection(
                name="plan_documents",
                embedding_function=self.embedding_fn
            )
            self.guidelines_coll = self.client.get_or_create_collection(
                name="clinical_guidelines",
                embedding_function=self.embedding_fn
            )
        else:
            self.client = None
            self.plan_coll = None
            self.guidelines_coll = None
        self._index_all()

    def _index_all(self):
        # 1. Index Plan Documents
        plan_files = glob.glob(os.path.join(DATA_DIR, "plan_documents", "*.md")) or \
                     glob.glob(os.path.join(DATA_DIR, "plan_docs", "*.md"))
        plan_dict = {}
        for fpath in plan_files:
            if not os.path.exists(fpath): continue
            with open(fpath, encoding="utf-8") as f:
                for line in f:
                    m = CLAUSE_REGEX.match(line.strip())
                    if m:
                        cid, text = m.group(1), m.group(2)
                        self.clause_lookup[cid] = text
                        plan_dict[cid] = f"{cid} {text}"

        if plan_dict:
            try:
                existing = self.plan_coll.get()["ids"]
                if existing: self.plan_coll.delete(ids=existing)
            except Exception: pass
            self.plan_coll.add(documents=list(plan_dict.values()), ids=list(plan_dict.keys()))

        # 2. Index Clinical Guidelines
        guide_files = glob.glob(os.path.join(DATA_DIR, "guidelines", "*.md"))
        guide_dict = {}
        for fpath in guide_files:
            if not os.path.exists(fpath): continue
            with open(fpath, encoding="utf-8") as f:
                for line in f:
                    m = CLAUSE_REGEX.match(line.strip())
                    if m:
                        cid, text = m.group(1), m.group(2)
                        self.clause_lookup[cid] = text
                        guide_dict[cid] = f"{cid} {text}"

        if guide_dict:
            try:
                existing = self.guidelines_coll.get()["ids"]
                if existing: self.guidelines_coll.delete(ids=existing)
            except Exception: pass
            self.guidelines_coll.add(documents=list(guide_dict.values()), ids=list(guide_dict.keys()))

    def retrieve(self, query: str, collection: str, k: int = 4) -> List[Dict[str, Any]]:
        if HAS_CHROMADB and self.plan_coll is not None:
            coll = self.plan_coll if "plan" in collection else self.guidelines_coll
            count = coll.count()
            if count == 0:
                return []
            n_results = min(k, count)
            res = coll.query(query_texts=[query], n_results=n_results)
            
            hits = []
            if res and res.get("ids") and res["ids"][0]:
                ids = res["ids"][0]
                dists = res.get("distances", [[0.0] * len(ids)])[0]
                docs = res.get("documents", [[""] * len(ids)])[0]
                for cid, dist, doc in zip(ids, dists, docs):
                    score = round(max(0.0, 1.0 - (dist if dist is not None else 0.0)), 3)
                    hits.append({
                        "clause_id": cid,
                        "text": self.clause_lookup.get(cid, doc),
                        "score": score
                    })
            return hits
        else:
            q_tokens = set(tokenize(query))
            scored = []
            prefix = "PLAN-" if "plan" in collection else "GL-"
            for cid, doc in self.clause_lookup.items():
                if not cid.startswith(prefix):
                    continue
                d_tokens = set(tokenize(cid + " " + doc))
                overlap = len(q_tokens & d_tokens)
                if overlap > 0:
                    scored.append((overlap, cid, doc))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [{"clause_id": c, "text": d, "score": round(s / max(1, len(q_tokens)), 3)} for s, c, d in scored[:k]]

    def get_clause_text(self, clause_id: str) -> str:
        return self.clause_lookup.get(clause_id, "")

# Singleton RAG engine instance
_engine = None
def get_rag() -> RAGEngine:
    global _engine
    if _engine is None:
        _engine = RAGEngine()
    return _engine

def retrieve(query: str, collection: str, k: int = 4) -> List[Dict[str, Any]]:
    return get_rag().retrieve(query, collection, k)

def get_clause_text(clause_id: str) -> str:
    return get_rag().get_clause_text(clause_id)
