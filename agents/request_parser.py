"""Request Parser Agent:
Extracts structured clinical referral entities from free-text pre-authorisation requests:
  - treatment
  - diagnosis
  - provider
  - plan
"""
import re
from typing import Dict, Any
from llm_client import with_fallback, ask_json

SYS_PROMPT = """You are a specialized Clinical Request Parser for healthcare utilization management.
Extract the following fields from the pre-authorisation request text:
- treatment: The exact clinical procedure, diagnostic scan, surgery, or medication requested.
- diagnosis: The reported clinical condition, symptom duration, previous treatments tried, or clinical indications.
- provider: The requesting physician, clinic, hospital, and network status if stated.
- plan: The insurance health plan mentioned (default to 'Gold-500' if unspecified).

Return ONLY a single valid JSON object with keys: "treatment", "diagnosis", "provider", "plan".
"""

async def _llm_parse(raw_text: str) -> Dict[str, str]:
    return await ask_json(SYS_PROMPT, f"PRE-AUTHORISATION REQUEST:\n{raw_text}")

def _rule_parse(raw_text: str) -> Dict[str, str]:
    t = raw_text.strip()
    
    # Treatment extraction
    tm = re.search(r"Request\s+([^.\n]+?)(?:\s+for\s+patient|\s+for\s+P-|\.\s*Diagnosis|\s+Diagnosis:)", t, re.I)
    treatment = tm.group(1).strip() if tm else "treatment requested"
    if "rhinoplasty" in t.lower(): treatment = "rhinoplasty"
    elif "mri lumbar" in t.lower(): treatment = "MRI lumbar spine"
    elif "knee replacement" in t.lower() or "tkr" in t.lower(): treatment = "total knee replacement"
    elif "chemotherapy" in t.lower(): treatment = "chemotherapy"
    elif "bariatric" in t.lower(): treatment = "bariatric surgery"
    elif "stem-cell" in t.lower(): treatment = "experimental stem-cell injection"
    elif "arthroscopy" in t.lower(): treatment = "knee arthroscopy"
    elif "knee surgery" in t.lower(): treatment = "knee surgery"
    elif "ct head" in t.lower(): treatment = "CT head scan"

    # Diagnosis extraction
    dm = re.search(r"Diagnosis:\s*([^.\n]+(?:\.[^.\n]+)*?)(?=\.\s*Provider:|\s*Provider:|\s*Plan:|$)", t, re.I)
    diagnosis = dm.group(1).strip() if dm else "clinical indications"

    # Provider extraction
    pm = re.search(r"Provider:\s*([^.\n]+?)(?=\.\s*Plan:|\s*Plan:|$)", t, re.I)
    provider = pm.group(1).strip() if pm else "Attending Provider"

    # Plan extraction
    plm = re.search(r"Plan:\s*([^.\n]+)", t, re.I)
    plan = plm.group(1).strip() if plm else "Gold-500"

    return {
        "treatment": treatment,
        "diagnosis": diagnosis,
        "provider": provider,
        "plan": plan
    }

async def run(case_record) -> Dict[str, str]:
    raw_text = case_record.get("raw_request", "")
    
    async def _run_llm(c):
        return await _llm_parse(raw_text)

    def _run_rule(c):
        return _rule_parse(raw_text)

    parsed = await with_fallback("Request Parser", _run_llm, _run_rule, case_record)
    case_record.record_write("parsed", parsed, written_by="Request Parser")
    return parsed

