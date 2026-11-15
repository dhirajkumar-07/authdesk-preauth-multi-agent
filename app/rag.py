"""Clause-level RAG. Chunks by clause (keeps clause ID), TF-IDF cosine retrieval, pure Python (no DB needed).
Two collections: plan_docs and guidelines. Swap in ChromaDB later if you want; the retrieve() signature stays the same."""
import re, math, glob, os
from collections import Counter

_data_candidates = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "authdesk-kit", "data"),
    os.path.join(os.getcwd(), "data"),
    os.path.join(os.getcwd(), "authdesk-kit", "data"),
]
DATA = next((p for p in _data_candidates if os.path.exists(p) and os.path.isdir(p)), _data_candidates[0])
CLAUSE = re.compile(r"^((?:PLAN|GL)(?:-[A-Z]+)?-\d+\.\d+)\s+(.+)$")
tok = lambda s: re.findall(r"[a-z0-9]+", s.lower())

class Index:
    def __init__(self, folder):
        self.docs = {}
        for f in sorted(glob.glob(os.path.join(DATA, folder, "*.md"))):
            for line in open(f, encoding="utf-8"):
                m = CLAUSE.match(line.strip())
                if m: self.docs[m.group(1)] = m.group(2)
        self.tf = {i: Counter(tok(i + " " + t)) for i, t in self.docs.items()}
        df = Counter(w for c in self.tf.values() for w in c)
        n = len(self.docs) or 1
        self.idf = {w: math.log((1 + n) / (1 + d)) + 1 for w, d in df.items()}
    def search(self, q, k=4):
        qt = Counter(tok(q)); out = []
        for i, c in self.tf.items():
            num = sum(qt[w] * c[w] * self.idf.get(w, 0) ** 2 for w in qt)
            den = math.sqrt(sum((v * self.idf[w]) ** 2 for w, v in c.items())) * math.sqrt(sum((v * self.idf.get(w, 1)) ** 2 for w, v in qt.items())) or 1
            out.append((num / den, i))
        out.sort(reverse=True)
        return [{"clause_id": i, "text": self.docs[i], "score": round(s, 3)} for s, i in out[:k] if s > 0]

COLLECTIONS = {"plan_docs": Index("plan_docs"), "guidelines": Index("guidelines")}
def retrieve(query, collection, k=4): return COLLECTIONS[collection].search(query, k)
def clause_text(cid):
    for c in COLLECTIONS.values():
        if cid in c.docs: return c.docs[cid]
    return ""
