"""Authorisation Manager Agent:
Merges findings from Coverage Retrieval and Medical Necessity, synthesizes the decision:
  - APPROVE: Coverage is COVERED_PRIOR_AUTH and Medical Necessity is MET.
  - DENY: Explicit policy exclusion (EXCLUDED) or clinical criterion failure (NOT_MET).
  - MORE_INFO: Ambiguous or incomplete clinical records (UNCLEAR / INSUFFICIENT).

Enforces strict grounding and records writes into the shared case record.
"""
from typing import Dict, Any, List
import rag
from llm_client import with_fallback, ask_json

SYS_PROMPT = """You are the Senior Healthcare Authorisation Manager.
Synthesize the findings from the Coverage Retrieval Agent and the Medical Necessity Agent into a final determination.

Determination Rules:
- APPROVE: Benefit is COVERED_PRIOR_AUTH AND Medical Necessity is MET.
- DENY: Explicit contractual exclusion (EXCLUDED) OR clinical guidelines NOT_MET.
- MORE_INFO: Policy is UNCLEAR OR clinical information is INSUFFICIENT to decide.

Cite ONLY the clause IDs present in the upstream findings.
Output valid JSON only:
{
  "decision": "APPROVE" | "DENY" | "MORE_INFO",
  "confidence": 0.0 to 1.0,
  "cited_clauses": ["PLAN-x.x", "GL-xxx-x.x"],
  "rationale": "Comprehensive explanation of the determination"
}
"""

def _rule_decision(cov: Dict[str, Any], nec: Dict[str, Any]) -> Dict[str, Any]:
    cov_st = cov.get("status", "UNCLEAR")
    nec_st = nec.get("status", "INSUFFICIENT")
    cov_clauses = cov.get("clauses", [])
    nec_clauses = nec.get("clauses", [])
    
    # 1. Denials
    if cov_st == "EXCLUDED":
        all_clauses = list(dict.fromkeys(cov_clauses + nec_clauses))
        return {
            "decision": "DENY",
            "confidence": 0.95,
            "cited_clauses": all_clauses or ["PLAN-4.1"],
            "rationale": f"Contractual plan exclusion applies: {cov.get('reason')}"
        }
    if nec_st == "NOT_MET":
        all_clauses = list(dict.fromkeys(cov_clauses + nec_clauses))
        return {
            "decision": "DENY",
            "confidence": 0.95,
            "cited_clauses": all_clauses,
            "rationale": f"Clinical medical necessity criteria are not satisfied: {nec.get('reason')}"
        }

    # 2. Incomplete / More Info
    if cov_st == "UNCLEAR" or nec_st == "INSUFFICIENT":
        all_clauses = list(dict.fromkeys(cov_clauses + nec_clauses))
        if "PLAN-7.2" not in all_clauses: all_clauses.append("PLAN-7.2")
        return {
            "decision": "MORE_INFO",
            "confidence": 0.90,
            "cited_clauses": all_clauses,
            "rationale": "Clinical records submitted are incomplete. Additional clinical information required prior to determination."
        }

    # 3. Approvals
    if cov_st == "COVERED_PRIOR_AUTH" and nec_st == "MET":
        all_clauses = list(dict.fromkeys(cov_clauses + nec_clauses))
        return {
            "decision": "APPROVE",
            "confidence": 0.95,
            "cited_clauses": all_clauses,
            "rationale": "Procedure is a covered benefit under Gold-500 plan and all evidence-based clinical guideline criteria are met."
        }

    # Fallback
    all_clauses = list(dict.fromkeys(cov_clauses + nec_clauses))
    return {
        "decision": "MORE_INFO",
        "confidence": 0.70,
        "cited_clauses": all_clauses or ["PLAN-7.2"],
        "rationale": "Clinical documentation requires further verification."
    }

async def run(case_record) -> Dict[str, Any]:
    cov = case_record.get("coverage_findings", {})
    nec = case_record.get("necessity_findings", {})
    valid_clauses = set(cov.get("clauses", []) + nec.get("clauses", []) + cov.get("retrieved", []) + nec.get("retrieved", []))

    async def _run_llm(c):
        user_msg = (
            f"COVERAGE FINDING: Status={cov.get('status')}, Clauses={cov.get('clauses')}, Reason={cov.get('reason')}\n"
            f"MEDICAL NECESSITY FINDING: Status={nec.get('status')}, Clauses={nec.get('clauses')}, Reason={nec.get('reason')}"
        )
        res = await ask_json(SYS_PROMPT, user_msg)
        # Grounding check
        res["cited_clauses"] = [cid for cid in res.get("cited_clauses", []) if cid in valid_clauses]
        if not res["cited_clauses"]:
            res["cited_clauses"] = list(dict.fromkeys(cov.get("clauses", []) + nec.get("clauses", [])))
        return res

    def _run_rule(c):
        return _rule_decision(cov, nec)

    decision_res = await with_fallback("Authorisation Manager", _run_llm, _run_rule, case_record)
    
    dec = decision_res["decision"]
    conf = decision_res.get("confidence", 0.9)
    cited = decision_res.get("cited_clauses", [])

    # Update case record fields with provenance
    case_record.record_write("ai_decision", dec, written_by="Authorisation Manager")
    case_record.record_write("decision", dec, written_by="Authorisation Manager")
    case_record.record_write("confidence", conf, written_by="Authorisation Manager")
    case_record.record_write("cited_clauses", cited, written_by="Authorisation Manager")

    # Update clause texts
    clause_texts = case_record.get("clause_text", {})
    for cid in cited:
        if cid not in clause_texts:
            clause_texts[cid] = rag.get_clause_text(cid)
    case_record["clause_text"] = clause_texts

    # Human routing
    if dec == "APPROVE":
        case_record.record_write("status", "COMPLETED", written_by="Authorisation Manager")
    else:
        # Every DENY and MORE_INFO triggers peer review escalation
        hr = {
            "required": True,
            "reviewer": None,
            "verdict": None,
            "notes": None,
            "timestamp": None
        }
        case_record.record_write("human_review", hr, written_by="Authorisation Manager")
        case_record.record_write("status", "PENDING_HUMAN_REVIEW", written_by="Authorisation Manager")

    return decision_res
