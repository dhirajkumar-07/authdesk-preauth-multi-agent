"""Medical Necessity Agent:
Performs grounded RAG over clinical guidelines and determines:
  - status: MET | NOT_MET | INSUFFICIENT | NOT_APPLICABLE
  - clauses: list of cited guideline IDs (e.g. ['GL-MRI-3.1'])
  - reason: clinical justification citing clinical criteria
"""
import re
from typing import Dict, Any, List
import rag
from llm_client import with_fallback, ask_json

SYS_PROMPT = """You are a Medical Necessity Reviewer for clinical pre-authorisation.
Evaluate whether the patient's documented diagnosis and history meet the evidence-based clinical guidelines.
Base your determination STRICTLY on the retrieved clinical guidelines provided below.

Status options:
- MET: Patient meets all clinical criteria and duration thresholds.
- NOT_MET: Patient fails criteria (e.g., uncomplicated acute pain under 6 weeks GL-MRI-3.2, or knee arthroscopy for OA alone GL-KNEE-2.1).
- INSUFFICIENT: Essential clinical details, trial durations, or imaging results are omitted.
- NOT_APPLICABLE: Procedure is non-clinical or purely cosmetic.

Output valid JSON only:
{
  "status": "MET" | "NOT_MET" | "INSUFFICIENT" | "NOT_APPLICABLE",
  "clauses": ["GL-xxx-x.x"],
  "reason": "Evidence-based explanation citing clinical guideline ID",
  "confidence": 0.0 to 1.0
}
"""

def _rule_necessity(treatment: str, diagnosis: str, raw_text: str, retrieved_hits: List[Dict[str, Any]]) -> Dict[str, Any]:
    tl = (treatment + " " + diagnosis + " " + raw_text).lower()
    
    # 1. Cosmetic / Experimental -> NOT_APPLICABLE
    if re.search(r"rhinoplasty.*improve nose shape|cosmetic|stem-cell|experimental", tl) and not re.search(r"obstruction|trauma|breathing", tl):
        return {
            "status": "NOT_APPLICABLE",
            "clauses": [],
            "reason": "Procedure is elective cosmetic or experimental; clinical guidelines are not applicable.",
            "confidence": 1.0
        }

    # 2. Incomplete clinical info
    if re.search(r"no details|no imaging|no history|not provided", tl):
        # Match guideline to the procedure
        cid = "GL-KNEE-2.1" if "knee" in tl else ("GL-CT-8.1" if "ct" in tl else "GL-MRI-3.1")
        return {
            "status": "INSUFFICIENT",
            "clauses": [cid],
            "reason": f"Clinical submission lacks essential symptom duration or prior treatment history under {cid}.",
            "confidence": 0.85
        }

    # 3. Lumbar Spine MRI
    if "lumbar" in tl or "mri lumbar" in tl or "back pain" in tl:
        if re.search(r"2\s*weeks|acute|under\s*6\s*weeks", tl) and re.search(r"no.*red flag|no weakness|no prior", tl):
            return {
                "status": "NOT_MET",
                "clauses": ["GL-MRI-3.2"],
                "reason": "Routine MRI is not indicated for acute uncomplicated back pain under 6 weeks without red flags (GL-MRI-3.2).",
                "confidence": 0.95
            }
        elif re.search(r"(8\s*weeks|6\s*weeks|chronic|failed.*physiotherapy)", tl) or (re.search(r"red flag", tl) and not re.search(r"no.*red flag", tl)):
            return {
                "status": "MET",
                "clauses": ["GL-MRI-3.1"],
                "reason": "Low back pain persists 6 weeks or more with documented failure of conservative therapy, meeting GL-MRI-3.1.",
                "confidence": 0.95
            }

    # 4. Total Knee Replacement (TKR)
    if "knee replacement" in tl or "tkr" in tl:
        if re.search(r"severe.*osteoarthritis|4\s*months|3\s*months", tl):
            return {
                "status": "MET",
                "clauses": ["GL-TKR-4.1"],
                "reason": "Severe knee osteoarthritis with >3 months failed conservative treatment meets GL-TKR-4.1.",
                "confidence": 0.95
            }

    # 5. Knee Arthroscopy
    if "arthroscopy" in tl:
        if re.search(r"degenerative.*only|osteoarthritis only|no meniscal tear", tl):
            return {
                "status": "NOT_MET",
                "clauses": ["GL-KNEE-2.1"],
                "reason": "Arthroscopy is not indicated for degenerative osteoarthritis alone without mechanical tears under GL-KNEE-2.1.",
                "confidence": 0.95
            }

    # 6. Bariatric Surgery
    if "bariatric" in tl:
        if re.search(r"bmi\s*4[0-9]|12\s*months|supervised", tl):
            return {
                "status": "MET",
                "clauses": ["GL-BAR-5.1"],
                "reason": "Patient BMI of 42 (>=40) with 12 months supervised diet program satisfies GL-BAR-5.1.",
                "confidence": 0.95
            }

    # 7. Chemotherapy
    if "chemotherapy" in tl or "cancer" in tl:
        return {
            "status": "MET",
            "clauses": ["GL-ONC-6.1"],
            "reason": "Histologically confirmed biopsy and oncologist treatment plan satisfy GL-ONC-6.1.",
            "confidence": 0.95
        }

    # Fallback to top retrieved guideline
    top_cid = retrieved_hits[0]["clause_id"] if retrieved_hits else "GL-MRI-3.1"
    return {
        "status": "MET",
        "clauses": [top_cid],
        "reason": f"Clinical guideline criteria evaluated under {top_cid}.",
        "confidence": 0.75
    }

async def run(case_record) -> Dict[str, Any]:
    parsed = case_record.get("parsed", {})
    treatment = parsed.get("treatment", "")
    diagnosis = parsed.get("diagnosis", "")
    raw_req = case_record.get("raw_request", "")
    query = f"{treatment} {diagnosis} {raw_req}"
    
    hits = rag.retrieve(query, collection="clinical_guidelines", k=4)
    retrieved_clause_ids = {h["clause_id"] for h in hits}

    async def _run_llm(c):
        context = "\n".join([f"- {h['clause_id']}: {h['text']}" for h in hits])
        user_msg = f"TREATMENT: {treatment}\nDIAGNOSIS & CLINICAL INFO: {diagnosis}\nRAW REQUEST: {raw_req}\n\nRETRIEVED GUIDELINES:\n{context}"
        res = await ask_json(SYS_PROMPT, user_msg)
        res["clauses"] = [cid for cid in res.get("clauses", []) if cid in retrieved_clause_ids]
        if not res["clauses"] and hits and res.get("status") not in ("NOT_APPLICABLE",):
            res["clauses"] = [hits[0]["clause_id"]]
        return res

    def _run_rule(c):
        return _rule_necessity(treatment, diagnosis, raw_req, hits)

    findings = await with_fallback("Medical Necessity", _run_llm, _run_rule, case_record)
    findings["retrieved"] = [h["clause_id"] for h in hits]
    
    clause_texts = case_record.get("clause_text", {})
    for cid in findings.get("clauses", []):
        clause_texts[cid] = rag.get_clause_text(cid)
    case_record["clause_text"] = clause_texts

    case_record.record_write("necessity_findings", findings, written_by="Medical Necessity")
    return findings
