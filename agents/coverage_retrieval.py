"""Coverage Retrieval Agent:
Performs grounded RAG over plan benefit documents (Gold-500) and returns:
  - status: COVERED_PRIOR_AUTH | EXCLUDED | UNCLEAR
  - clauses: list of matching clause IDs (e.g. ['PLAN-2.1', 'PLAN-7.1'])
  - reason: policy explanation citing contractual clauses
"""
import re
from typing import Dict, Any, List
import rag
from llm_client import with_fallback, ask_json

SYS_PROMPT = """You are a Health Plan Coverage Verification Specialist.
Your task is to determine whether the requested treatment is COVERED, EXCLUDED, or UNCLEAR under the member's benefit plan.
Base your determination STRICTLY on the retrieved plan clauses provided below. Do not assume or cite clauses not in the retrieved list.

Status options:
- COVERED_PRIOR_AUTH: The procedure is a covered benefit requiring prior authorization.
- EXCLUDED: The procedure is explicitly excluded (e.g., cosmetic PLAN-4.1, experimental PLAN-4.2, out-of-network PLAN-4.3).
- UNCLEAR: The documentation is missing or insufficient to confirm benefit coverage (PLAN-7.2).

Output valid JSON only:
{
  "status": "COVERED_PRIOR_AUTH" | "EXCLUDED" | "UNCLEAR",
  "clauses": ["PLAN-x.x"],
  "reason": "Clear justification citing clauses",
  "confidence": 0.0 to 1.0
}
"""

def _rule_coverage(treatment: str, raw_text: str, retrieved_hits: List[Dict[str, Any]]) -> Dict[str, Any]:
    tl = (treatment + " " + raw_text).lower()
    hit_ids = {h["clause_id"] for h in retrieved_hits}
    
    # 1. Cosmetic exclusion
    if re.search(r"rhinoplasty|cosmetic|appearance|nose shape", tl):
        if not re.search(r"(airway\s+obstruction|severe.*obstruction|traumatic\s+deformity|documented\s+fracture)", tl):
            return {
                "status": "EXCLUDED",
                "clauses": ["PLAN-4.1"],
                "reason": "Cosmetic procedures performed to improve appearance without functional medical need are excluded under PLAN-4.1.",
                "confidence": 1.0
            }
    
    # 2. Experimental / investigational exclusion
    if re.search(r"experimental|investigational|stem-cell|unproven", tl):
        return {
            "status": "EXCLUDED",
            "clauses": ["PLAN-4.2"],
            "reason": "Experimental, investigational or unproven treatments are excluded under PLAN-4.2.",
            "confidence": 1.0
        }
    
    # 3. Out-of-network exclusion
    if "out-of-network" in tl and "emergency" not in tl:
        return {
            "status": "EXCLUDED",
            "clauses": ["PLAN-4.3"],
            "reason": "Services from out-of-network providers are excluded except in emergencies under PLAN-4.3.",
            "confidence": 1.0
        }

    # 4. Incomplete documentation
    if re.search(r"no details|no imaging|no history|not provided", tl):
        return {
            "status": "UNCLEAR",
            "clauses": ["PLAN-7.2"],
            "reason": "Clinical documentation submitted is incomplete; additional information required under PLAN-7.2.",
            "confidence": 0.8
        }

    # 5. Diagnostic imaging
    if re.search(r"mri|ct scan|pet scan", tl):
        return {
            "status": "COVERED_PRIOR_AUTH",
            "clauses": ["PLAN-2.1", "PLAN-7.1"],
            "reason": "Diagnostic imaging is covered when medically necessary with prior authorization under PLAN-2.1 and PLAN-7.1.",
            "confidence": 0.95
        }

    # 6. Surgery & Joint Replacement
    if re.search(r"replacement|surgery|arthroscopy|knee", tl):
        if "bariatric" in tl:
            return {
                "status": "COVERED_PRIOR_AUTH",
                "clauses": ["PLAN-2.4", "PLAN-7.1"],
                "reason": "Bariatric surgery is covered subject to clinical guidelines and prior authorization under PLAN-2.4 and PLAN-7.1.",
                "confidence": 0.95
            }
        return {
            "status": "COVERED_PRIOR_AUTH",
            "clauses": ["PLAN-2.2", "PLAN-7.1"],
            "reason": "Surgeries including joint replacements are covered with prior authorization under PLAN-2.2 and PLAN-7.1.",
            "confidence": 0.95
        }

    # 7. Oncology / Chemotherapy
    if re.search(r"chemotherapy|cancer|oncology", tl):
        return {
            "status": "COVERED_PRIOR_AUTH",
            "clauses": ["PLAN-3.1", "PLAN-7.1"],
            "reason": "Chemotherapy is covered with prior authorization under an oncologist's plan under PLAN-3.1 and PLAN-7.1.",
            "confidence": 0.95
        }

    # Default fallback to top retrieved clause
    top_cid = retrieved_hits[0]["clause_id"] if retrieved_hits else "PLAN-7.1"
    return {
        "status": "COVERED_PRIOR_AUTH",
        "clauses": [top_cid, "PLAN-7.1"],
        "reason": f"Covered subject to prior authorization under {top_cid}.",
        "confidence": 0.8
    }

async def run(case_record) -> Dict[str, Any]:
    parsed = case_record.get("parsed", {})
    treatment = parsed.get("treatment", "")
    raw_req = case_record.get("raw_request", "")
    query = f"{treatment} {raw_req}"
    
    # Retrieve top clauses from plan_documents collection
    hits = rag.retrieve(query, collection="plan_documents", k=4)
    retrieved_clause_ids = {h["clause_id"] for h in hits}

    async def _run_llm(c):
        context = "\n".join([f"- {h['clause_id']}: {h['text']}" for h in hits])
        user_msg = f"REQUESTED TREATMENT: {treatment}\nCLINICAL DETAILS: {raw_req}\n\nRETRIEVED PLAN CLAUSES:\n{context}"
        res = await ask_json(SYS_PROMPT, user_msg)
        # Ensure only retrieved clauses are cited (prevents hallucination)
        res["clauses"] = [cid for cid in res.get("clauses", []) if cid in retrieved_clause_ids]
        if not res["clauses"] and hits:
            res["clauses"] = [hits[0]["clause_id"]]
        return res

    def _run_rule(c):
        return _rule_coverage(treatment, raw_req, hits)

    findings = await with_fallback("Coverage Retrieval", _run_llm, _run_rule, case_record)
    findings["retrieved"] = [h["clause_id"] for h in hits]
    
    # Update clause texts
    clause_texts = case_record.get("clause_text", {})
    for cid in findings.get("clauses", []):
        clause_texts[cid] = rag.get_clause_text(cid)
    case_record["clause_text"] = clause_texts

    case_record.record_write("coverage_findings", findings, written_by="Coverage Retrieval")
    return findings
