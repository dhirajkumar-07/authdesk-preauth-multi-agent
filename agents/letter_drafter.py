"""Letter Drafter Agent:
Generates a legally compliant, clause-grounded determination letter:
  - Approval: Authorisation details, validity, in-network coordination.
  - Denial: Cites policy exclusions or clinical guideline non-fulfillment, outlines peer-review verdict and member appeal rights.
  - More Info: Specifies missing records, tests, or clinical duration notes needed.
"""
from typing import Dict, Any
from llm_client import with_fallback, ask_text

SYS_PROMPT = """You are a Health Plan Letter Drafter.
Write a formal, clear, and compassionate pre-authorisation determination letter.
Requirements:
1. State the FINAL DECISION clearly at the outset (APPROVED, DENIED, or ADDITIONAL INFORMATION REQUIRED).
2. Explicitly cite each cited policy clause ID and summarize its clinical or benefit text.
3. For denials, explain that the decision was reviewed under peer review escalation and specify the 60-day appeal rights under PLAN-7.3.
4. For more-info requests, state exactly what clinical records must be submitted under PLAN-7.2.
5. Plain professional text under 250 words.
"""

def _rule_letter(case_record) -> str:
    p = case_record.get("parsed", {})
    treatment = p.get("treatment", "the requested procedure")
    provider = p.get("provider", "Attending Provider")
    patient = p.get("patient", "Valued Member")
    plan = p.get("plan", "Gold-500 Comprehensive Plan")
    dec = case_record.get("decision", "PENDING")
    cid_list = case_record.get("cited_clauses", [])
    texts = case_record.get("clause_text", {})
    hr = case_record.get("human_review", {})

    clauses_block = "\n".join([f"  • [{cid}]: {texts.get(cid, 'Policy reference')}" for cid in cid_list])

    if dec == "APPROVE":
        return f"""PRE-AUTHORISATION DETERMINATION: APPROVED
Reference ID: {case_record.case_id}
Date: {case_record.created}
Plan: {plan}
Provider: {provider}

Dear {patient},

We are pleased to inform you that the prior-authorisation request for {treatment} has been APPROVED. 

Basis for Approval:
{clauses_block}

Clinical guidelines and benefit coverage policies for this procedure have been fully satisfied. This authorization is valid for 180 days from the date of this letter for services rendered by participating in-network providers.

Sincerely,
Utilization Management Committee
SynthCare Health Plan"""

    elif dec == "DENY":
        peer_note = f"\nClinical Peer Reviewer: {hr.get('reviewer', 'Senior Medical Director')}\nVerdict: {hr.get('verdict', 'UPHELD')} - Note: {hr.get('notes', 'Exclusion/criteria verified.')}\n" if hr.get("verdict") else ""
        return f"""PRE-AUTHORISATION DETERMINATION: ADVERSE DETERMINATION (DENIED)
Reference ID: {case_record.case_id}
Date: {case_record.created}
Plan: {plan}
Provider: {provider}

Dear {patient},

Following comprehensive clinical utilization review, the prior-authorisation request for {treatment} has been DENIED.{peer_note}
Applicable Policy Clauses & Guidelines:
{clauses_block}

Appeal Rights:
Under PLAN-7.3, you or your treating physician have the right to appeal this decision within 60 calendar days of receipt. To request an expedited peer-to-peer physician conference or submit supplementary medical records, please contact our Appeals Unit.

Sincerely,
Medical Review & Appeals Directorate
SynthCare Health Plan"""

    else: # MORE_INFO
        return f"""PRE-AUTHORISATION DETERMINATION: ADDITIONAL INFORMATION REQUIRED
Reference ID: {case_record.case_id}
Date: {case_record.created}
Plan: {plan}
Provider: {provider}

Dear {patient},

We have received the pre-authorisation referral for {treatment}. At this time, the submitted documentation is incomplete to establish medical necessity under PLAN-7.2.

Required Policy Documentation:
{clauses_block}

Action Required:
Please submit complete clinical consultation notes, relevant radiographic imaging reports, and documented history of conservative therapy within 30 calendar days to complete the evaluation.

Sincerely,
Utilization Review Department
SynthCare Health Plan"""

async def run(case_record) -> str:
    async def _run_llm(c):
        p = case_record.get("parsed", {})
        cites = "\n".join([f"- {cid}: {case_record.get('clause_text', {}).get(cid, '')}" for cid in case_record.get("cited_clauses", [])])
        user_msg = (
            f"CASE ID: {case_record.case_id}\n"
            f"PATIENT: {p.get('patient')}\n"
            f"TREATMENT: {p.get('treatment')}\n"
            f"PROVIDER: {p.get('provider')}\n"
            f"FINAL DECISION: {case_record.get('decision')}\n"
            f"HUMAN REVIEW: {case_record.get('human_review')}\n"
            f"CITED CLAUSES:\n{cites}"
        )
        return await ask_text(SYS_PROMPT, user_msg)

    def _run_rule(c):
        return _rule_letter(case_record)

    letter = await with_fallback("Letter Drafter", _run_llm, _run_rule, case_record)
    case_record.record_write("letter", letter, written_by="Letter Drafter")
    return letter

